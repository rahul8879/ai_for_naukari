from pathlib import Path
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from dotenv import load_dotenv
load_dotenv()

# 1 load your vector db
BASE_DIR = Path(__file__).resolve().parent

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")  

# laoding the vd
vectorstore = Chroma(
    collection_name="bajaj_policy",
    embedding_function=embedding_model,
    persist_directory=BASE_DIR / "bajajbot_chroma_db",
)


retreival = vectorstore.as_retriever(
   search_type = 'mmr',
   search_kwargs={'k': 3,
                  'fetch_k': 10,
                  "lambda_mult": 0.7,
                  'threshold': 0.9
                    }
)



prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Bajaj Finance helpdesk agent.
Answer the customer query using ONLY the policy context below.

STRICT RULES:
- Use ONLY the POLICY CONTEXT provided — never use general knowledge
- If answer is not in context, say exactly:
  "I don't have information on this. Please contact Rahul @ 9152091676."
- Never say "based on general practices" or "typically"
- Never make up numbers, rates, or policies
- Format amounts with Rs and commas (e.g., Rs 8,450)
- "minimum CIBIL score" means the score required for APPROVAL

POLICY CONTEXT:
{context}"""),

    # Chat history goes here — LLM sees previous turns for follow-up context
    MessagesPlaceholder(variable_name="chat_history"),

    ("human", "{query}"),
])


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


def format_context(docs):
    if not docs:
        return "I don't have information on this. Please contact Rahul @ 9152091676."
    return "\n".join([f"## {doc.page_content}" for doc in docs])



rag_chain = (
    { "context"     : RunnableLambda(lambda x: x["query"]) | retreival | format_context,
    "chat_history": RunnableLambda(lambda x: x["chat_history"]),
    "query"       : RunnableLambda(lambda x: x["query"]),}
    | prompt
    | llm
    | StrOutputParser()
)


def rag_answer(query, chat_history=[]):
    return rag_chain.invoke({"query": query, "chat_history": chat_history})


print(rag_answer('what is the minimum document needed to get the gold loan'))


