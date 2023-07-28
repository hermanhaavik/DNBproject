from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from typing import Any, Sequence

import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines
import time

class ChatRetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    prompt_prefix = """<|im_start|>system
You are an assistant helps the customers of DNB bank with their questions about insurance, your name is Floyd. Be brief in your answers. Only answer questions about DNB insurance. If you get questions about other insurance providers, tell a joke about insurance. 
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
Make sure to be polite and if its a question you cant answer guide the customers to either a branch office or https://www.dnb.no/en/insurance/house-insurance. 
It is very very important that you only answer questions that are DNB related or insurance related. Nothing else shall be answered, just state you dont know.
{follow_up_questions_prompt}
{injected_prompt}
Sources:
{sources}
<|im_end|>
{chat_history}
"""

    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about their insurance. 
    Use double angle brackets to reference the questions, e.g. <<Are there exclusions for prescriptions?>>.
    Try not to repeat questions that have already been asked.
    Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about insurance.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
"""

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.query = ""

    def __source_url_from_doc(self, doc: dict[str, str]):
        # sourcepage = doc[self.sourcepage_field]
        # without_suffix = re.sub(r'-(\d+)\.pdf$', '.pdf', sourcepage)
        # return without_suffix.replace('__', '/')
        return doc["sourceurl"]

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        print("Starting answering process")
        start_time = time.time()
        max_time_limit = 30

        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
    
        step_time = time.time()
        print("Beginning step 1: Generate keyword search query")

        self.query = history[-1]["user"]
        print(self.query)
        prompt = self.query_prompt_template.format(chat_history=self.get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        
        future = self.executor.submit(self.get_completion, prompt, overrides)
        try:
            var = time.time()
            completion = future.result(timeout=max_time_limit)
            print(f"Time for OpenAI to generate an improved Query {time.time() - var}")
        except concurrent.futures.TimeoutError:
            # Custom response for when it takes to long
            print(f"Amount of time before timeout: {time.time()- step_time} seconds.")
            return {"data_points": "no results were created", "answer": "Took to long for OpenAI to generate a query, please try again:)", "thoughts": "Didnt manage search"}
        
        q = completion.choices[0].text
   
        print("Beginning step 2: Retrieve document from search index")
        step_time = time.time()

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)

        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        print(f"Finished step 2 in {time.time() - step_time} seconds")

        print("Beginning step 3: Generate question answer")
        step_time = time.time()

        follow_up_questions_prompt = self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else ""
        
        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            prompt = self.prompt_prefix.format(injected_prompt="", sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)
        elif prompt_override.startswith(">>>"):
            prompt = self.prompt_prefix.format(injected_prompt=prompt_override[3:] + "\n", sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)
        else:
            prompt = prompt_override.format(sources=content, chat_history=self.get_chat_history_as_text(history), follow_up_questions_prompt=follow_up_questions_prompt)

        print(f"Max time limit for question answering has been set to {max_time_limit} seconds")

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history, 
        print("Starting question answering thread")
        future = self.executor.submit(self.get_completion,prompt, overrides)
        timer1 = time.time()
        try:
            completion = future.result(timeout=max_time_limit)
        except TimeoutError:
            print(f"Answer generation timed out... Took more than {max_time_limit} seconds, actual time waiting for response from OpenAI was {time.time()-timer1} seconds")
            return {"data_points": results, "answer": "Took to long to find an answer, please try again:)", "thoughts": f"Searched for:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}

        answer = completion.choices[0].text

        print(f"Finished step 3 in {time.time() - step_time} seconds")

        print(f"Answering process completed in {time.time() - start_time} seconds")

        
    
        # STEP 4: Ask GPT if its pleased with its answer
        print("Asking GPT if its pleased with its answer")
        new_prompt_for_confirmation_template = """Is the following Answer good given the question?
       

        

        Here is the question asked: {question}

        Here is the answer: {answer_for_check}
        
        """
        new_prompt = new_prompt_for_confirmation_template.format( question=self.query, answer_for_check=answer)
        
        print(new_prompt)
    
        future = self.executor.submit(self.get_completion, new_prompt, overrides )
        timer1 = time.time()
        try:
            completion = future.result(timeout=max_time_limit)
        except TimeoutError:
            print(f"Couldnt verify answer, actual time waiting for response from OpenAI was {time.time()-timer1} seconds")
            return {"data_points": results, "answer": "Couldnt verify answer)", "thoughts": f"Searched for:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
        

        print("SNART HELG :)")
        print(completion.choices[0].text)


        print(f"Finished step 3 in {time.time() - step_time} seconds")

        print(f"Answering process completed in {time.time() - start_time} seconds")



        # ----------------------------------------------   STEP 4 FINISHED   ----------------------------------------------




        return {"data_points": results, "answer": answer, "thoughts": f"Searched for:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
    def get_chat_history_as_text(self, history: Sequence[dict[str, str]], include_last_turn: bool=True, approx_max_tokens: int=1000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """<|im_start|>user""" + "\n" + h["user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (h.get("bot", "") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text

    def get_completion(self, prompt, overrides):
        return openai.Completion.create(
            engine=self.chatgpt_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0, 
            max_tokens=1024, 
            n=1, 
            stop=["<|im_end|>", "<|im_start|>"]
            )