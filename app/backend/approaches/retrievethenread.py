import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from text import nonewlines
from typing import Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError


class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    template = \
"You are an intelligent assistant named Floyd, like the boxer, helping DNB Bank ASA customers with their questions about insurance. " + \
"When someone interacts with you, they are interacting with DNB, so behave like you are representing DNB" + \
"Use 'you' to refer to the individual asking the questions even if they ask with 'I'. " + \
"Answer the following question using only the data provided in the sources below. " + \
"For tabular information return it as an html table. Do not return markdown format. "  + \
"Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. " + \
"Remember to include the source name for each fact you use in the response." + \
"Dont repeat yourself, if you have stated something earlier in the answer dont say it again." + \
"If you cannot answer using the sources below, say you don't know, and tell them to reach out to customer support. " + \
"When you say that someone has to reach out to customer support you also give them this link: ""https://www.dnb.no/hjelp-og-veiledning"", aswell as a short summary of what they should ask customer service based on this conversation "+\
"Before you conclude with an answer, make sure you follow the rules mentioned above" +\
"""

###
Question: 'Does my treatment medical insurance cover a CT scan in Denmark?'

Sources:
info1.txt: The insurance covers diagnostic imaging within 10 working days, for example MRI and CT scans
info2.pdf: The insurance applies to treatment in Norway, Sweden and Denmark (Scandinavia). If no expertise is available in Scandinavia, referrals can be made to other private treatment institutions in Europe with whom the company has an agreement.
info3.pdf: The insurance covers medical helpline. 
info4.pdf: The insurance does not cover treatment for illnesses, injuries, or ailments that occurred prior to the insurance's approval.

Answer: The insurance covers diagnostic imaging within 10 working days, such as MRI and CT scans [info1.txt]. It applies to treatment in Scandinavia, including Denmark [info2.pdf]. However, it does not cover treatment for illnesses, injuries, or ailments that occurred before the insurance's approval [info4.pdf].
###

Question: '{q}'?

Sources:
{retrieved}

Answer:
"""

    def __init__(self, search_client: SearchClient, openai_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field



    def run(self, q: str, overrides: dict[str, Any]) -> Any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

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

        prompt = (overrides.get("prompt_template") or self.template).format(q=q, retrieved=content)

        
        #Setting max time limit for OpenAI search
        max_time_limit = 4


        #Start the threading, if the get_completion method takes to long(max_time_limit) the TimeoutError is triggered.
        try:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self.get_completion, prompt, overrides)
                completion = future.result(timeout=max_time_limit)
        
        except TimeoutError:
            #Custom response for when it takes to long
            return {"data_points": results, "answer": "Request took too long to generate, pleasre try again:=)", "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
        
        #Regular response for when timeouts doesnt happen.
        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}


    #Query for the completion from OpenAI
    def get_completion(self, prompt, overrides):
        return openai.Completion.create(
            engine = self.openai_deployment,
            prompt = prompt,
            temperature = overrides.get("temperature") or 0.3,
            max_tokens = 1024,
            n = 1,
            stop = ["\n"]

        )
       
    """
        #Setting the starttime for the counter
        start_time = time.time()
        completion = openai.Completion.create(
            engine=self.openai_deployment,
            stream=True,
            prompt=prompt,
            temperature=overrides.get("temperature") or 0.3,
            max_tokens=1024,
            n=1,
            stop=["\n"]
)
        
        #Finding how long has elapsed since start of request
        elapsed_time = time.time()- start_time

        if (elapsed_time >= 10):
            return {"data_points": results, "answer": "Request took to long... Please try again", "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
    

    """