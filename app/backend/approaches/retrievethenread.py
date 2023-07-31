import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from text import nonewlines
from typing import Any




class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    template = \
    "You can speak a varied range of language, especially Norwegian " +\
"Use the language the customer uses in your answer even tho you dont know the answer." +\
"You are an intelligent assistant named Floyd, like the boxer, helping DNB Bank ASA customers with their questions about insurance. " + \
"When someone interacts with you, they are interacting with DNB" + \
"Use 'you' to refer to the individual asking the questions even if they ask with 'I'. " + \
"Answer the following question using only the data provided in the sources below. " + \
"For tabular information return it as an html table. Do not return markdown format. "  + \
"Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. " + \
"Remember to include the source name for each fact you use in the response." + \
"If you cannot answer using the sources below, say you don't know, and tell them to reach out to customer support. " + \
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
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r if doc["@search.score"] >= 1]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r if doc["@search.score"] >= 1]
        content = "\n".join(results)

        prompt = (overrides.get("prompt_template") or self.template).format(q=q, retrieved=content)
        completion = openai.Completion.create(
            engine=self.openai_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0, 
            max_tokens=1024, 
            n=1, 

            stop=["\n"])

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
