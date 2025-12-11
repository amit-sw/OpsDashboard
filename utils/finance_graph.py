from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage

def create_llm_msg(system_prompt,history, revenue_str):
    resp=[SystemMessage(content=system_prompt), HumanMessage(content=revenue_str)]
    msgs = history
    for m in msgs:
        if m["role"] == "user":
            resp.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            resp.append(AIMessage(content=m["content"]))
    #print(f"DEBUG CREATE LLM MSGS: {history=}\n{resp=}")
    return resp

class AgentState(BaseModel):
    """State of the agent."""
    messages: list = []
    revenue_str: str
    response: str = ""
    category: str = ""
    number_of_days: int = 0
    output_format: str = ""

class CategoryDaysOutput(BaseModel):
    """Category for the agent. Also the time period for which we need inidividual daily records"""
    category: str
    number_of_days: int
    output_format: str

class FinancebotAgent():
    """A chatbot agent that interacts with users."""

    def __init__(self, api_key: str):
        self.model = ChatOpenAI(model_name="gpt-5-nano", openai_api_key=api_key)
        workflow = StateGraph(AgentState)
        workflow.add_node("classifier", self.classifier)
        workflow.add_node("smalltalk_agent", self.smalltalk_agent)
        workflow.add_node("data_analysis_agent", self.data_analysis_agent)
        workflow.add_node("chart_agent", self.chart_agent)
        workflow.add_node("feedback_agent", self.feedback_agent)
        workflow.add_edge(START, "classifier")
        workflow.add_conditional_edges("classifier", self.main_router)
        #workflow.add_edge("classifier", "smalltalk_agent")
        #workflow.add_edge("classifier", "complaint_agent")
        #workflow.add_edge("classifier", "status_agent")
        #workflow.add_edge("classifier", "feedback_agent")
        workflow.add_edge("smalltalk_agent", END)
        workflow.add_edge("data_analysis_agent", END)
        workflow.add_edge("chart_agent", END)
        workflow.add_edge("feedback_agent", END)

        self.graph = workflow.compile()



    def classifier(self, state: AgentState):
        #print("Initial classsifier")
        messages=state.messages
        CLASSIFIER_PROMPT = """
        You are a helpful assistant that classifies input user messages for further processing.
        Three aspects:
        1. Given the user request, classify them into one of the following categories:
        - smalltalk_agent
        - data_analysis_agent
        - chart_agent
        - feedback_agent

        If you don't know the category, classify it as "smalltalk_agent".
        
        2. Determine the number of days for which you need individual transaction information. Return it as 'number_of_days'
        If no individual transaction information is needed, return zero.
        
        3. Determine the output format. Should we respond with 'text','csv', or 'image'.
        If in doubt, say "text"
        """
        llm_messages = create_llm_msg(CLASSIFIER_PROMPT, state.messages, state.revenue_str)
        llm_response = self.model.with_structured_output(CategoryDaysOutput).invoke(llm_messages)
        category=llm_response.category
        number_of_days=llm_response.number_of_days
        output_format=llm_response.output_format
        print(f"Classified category: {category} for {llm_response=}")
        return {"category":category,"number_of_days":number_of_days,"output_format":output_format}

    def main_router(self, state: AgentState):
        #print("Routing to appropriate agent based on category")
        #print(f"DEBUG: Current state: {state}")
        #print(f"DEBUG: Current category: {state.category}")
        return state.category

    def smalltalk_agent(self, state: AgentState):
        print("Smalltalk agent processing....")
        SMALLTALK_PROMPT = f"""
        You are a smalltalk agent that engages in casual conversation.
        Given the following messages, respond appropriately to the user's message.
        """
        llm_messages = create_llm_msg(SMALLTALK_PROMPT, state.messages, state.revenue_str)
        llm_response=self.model.invoke(llm_messages)
        return {"response": llm_response.content, "category": "smalltalk_agent"}

    def data_analysis_agent(self, state: AgentState):
        print("Data analysis agent processing....")
        DATA_ANALYSIS_PROMPT = f"""
        You are a Data Analyst.
        Respond to the user with information requested based on Transaction data.
        If you need to clarify requirements or need additional information, please say so.
        """
        llm_messages = create_llm_msg(DATA_ANALYSIS_PROMPT, state.messages, state.revenue_str)
        llm_response=self.model.invoke(llm_messages)
        return {"response": llm_response.content, "category": "data_analysis_agent"}


    def chart_agent(self, state: AgentState):
        print("Chart agent processing....")
        CHART_PROMPT = f"""
        You are a Graph Expert.
        Respond to the user with graph based on Transaction data.
        If you need to clarify requirements or need additional information, please say so.
        """
        llm_messages = create_llm_msg(CHART_PROMPT, state.messages, state.revenue_str)
        llm_response=self.model.invoke(llm_messages)
        return {"response": llm_response.content, "category": "chart_agent"}

    def feedback_agent(self, state: AgentState):
        print("Feedback agent processing....")
        FEEDBACK_PROMPT = f"""
        You are a feedback agent that collects user feedback.
        Given the following messages, respond appropriately to the user's feedback.
        """
        llm_messages = create_llm_msg(FEEDBACK_PROMPT, state.messages, state.revenue_str)
        return {"response": self.model.stream(llm_messages), "category": "feedback_agent"}