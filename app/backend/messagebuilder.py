# from __future__ import annotations
# import tiktoken

# class MessageBuilder:
#     """
#       A class for building and managing messages in a chat conversation.
#       Attributes:
#           message (list): A list of dictionaries representing chat messages.
#           model (str): The name of the ChatGPT model.
#           token_count (int): The total number of tokens in the conversation.
#       Methods:
#           __init__(self, system_content: str, chatgpt_model: str): Initializes the MessageBuilder instance.
#           append_message(self, role: str, content: str, index: int = 1): Appends a new message to the conversation.
#       """
#     AOAI_2_OAI = {
#     "gpt-35-turbo": "gpt-3.5-turbo",
#     "gpt-35-turbo-16k": "gpt-3.5-turbo-16k"
#     }

#     MODELS_2_TOKEN_LIMITS = {
#     "gpt-35-turbo": 4000,
#     "gpt-3.5-turbo": 4000,
#     "gpt-35-turbo-16k": 16000,
#     "gpt-3.5-turbo-16k": 16000,
#     "gpt-4": 8100,
#     "gpt-4-32k": 32000
#     }

#     def get_oai_chatmodel_tiktok(aoaimodel: str) -> str:
#         message = "Expected Azure OpenAI ChatGPT model name"
#         if aoaimodel == "" or aoaimodel is None:
#             raise ValueError(message)
#         if aoaimodel not in AOAI_2_OAI and aoaimodel not in MODELS_2_TOKEN_LIMITS:
#             raise ValueError(message)
#         return AOAI_2_OAI.get(aoaimodel) or aoaimodel

#     def num_tokens_from_messages(message: dict[str, str], model: str) -> int:
#         """
#         Calculate the number of tokens required to encode a message.
#         Args:
#             message (dict): The message to encode, represented as a dictionary.
#             model (str): The name of the model to use for encoding.
#         Returns:
#             int: The total number of tokens required to encode the message.
#         Example:
#             message = {'role': 'user', 'content': 'Hello, how are you?'}
#             model = 'gpt-3.5-turbo'
#             num_tokens_from_messages(message, model)
#             output: 11
#         """
#         encoding = tiktoken.encoding_for_model(get_oai_chatmodel_tiktok(model))
#         num_tokens = 2  # For "role" and "content" keys
#         for key, value in message.items():
#             num_tokens += len(encoding.encode(value))
#         return num_tokens

#     def __init__(self, system_content: str, chatgpt_model: str):
#         self.messages = [{'role': 'system', 'content': system_content}]
#         self.model = chatgpt_model
#         self.token_length = num_tokens_from_messages(
#             self.messages[-1], self.model)

#     def append_message(self, role: str, content: str, index: int = 1):
#         self.messages.insert(index, {'role': role, 'content': content})
#         self.token_length += num_tokens_from_messages(
#             self.messages[index], self.model)
        

    
    