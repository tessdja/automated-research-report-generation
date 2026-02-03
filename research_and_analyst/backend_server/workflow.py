import os
import sys
from datetime import datetime
from typing import Optional
from langgraph.types import Send

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import get_buffer_string
#from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_tavily import TavilySearch

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from research_and_analyst.backend_server.models import (
    Analyst,
    Perspectives,
    GenerateAnalystsState,
    InterviewState,
    ResearchGraphState,
    SearchQuery
)

from research_and_analyst.utils.model_loader import ModelLoader
from research_and_analyst.prompt_lib.prompts import *


def build_interview_graph(llm, tavily_search=None):
    """ Create a LangGraph subgraph that handles interviews."""

    memory = MemorySaver()

    def generation_question(state: InterviewState):
        """_summary_

        Args:
            state (InterviewState): _description_
        """
        analyst = state["analyst"]
        messages = state["messages"]

        # generate the question
        system_message = ANALYST_ASK_QUESTIONS.format(goals = analyst.persona)
        question = llm.invoke([SystemMessage(content=system_message)]+messages)

        # return the question through state
        return {"messages":[question]}
    
    def search_web(state: InterviewState):
        """_summary_

        Args:
            state (InterviewState): _description_
        """
        structure_llm = llm.with_structured_output(SearchQuery)
        search_query = structure_llm.invoke([GENERATE_SEARCH_QUERY]+state["messages"])

        # Search
        search_docs = tavily_search.invoke(search_query.search_query)
        # Format
        formatted_search_docs = "\n\n---\n\n".join(
            [
                f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
                for doc in search_docs
            ]
        )

        return {"context": [formatted_search_docs]}

    def generate_answer(state: InterviewState):
        """_summary_

        Args:
            state (InterviewState): _description_
        """
        # Get state
        analyst = state["analyst"]
        messages = state["messages"]
        context = state["context"]

        # Answer question
        system_message = GENERATE_ANSWERS.format(goals=analyst.persona, context=context)
        answer = llm.invoke([SystemMessage(content=system_message)]+messages)

        # Name the message as coming from the expert
        answer.name = "expert"

        # Append it to state
        return {"messages": [answer]}

    def save_interview(state: InterviewState):
        """_summary_

        Args:
            state (InterviewState): _description_
        """
        # Get messages
        messages = state["messages"]

        # Convert interview to a string
        interview = get_buffer_string(messages)

        # Save to interview key
        return {"interview": interview}

    def write_section(state: InterviewState):
        """_summary_

        Args:
            state (InterviewState): _description_
        """
        # Get state
        context = state["context"]
        analyst = state["analyst"]

        # Write section using either the gathered source docs from interview (context) 
        # or the interview itself (interview)
        system_message = WRITE_SECTION.format(focus=analyst.description)
        section = llm.invoke([SystemMessage(content=system_message)]+
                            [HumanMessage(content=f"Use this source to write your section: {context}")])

        # Append it to state
        return {"sections":[section.content]}

    builder = StateGraph(InterviewState)
    builder.add_node("ask_question", generation_question)
    builder.add_node("search_web", search_web)
    builder.add_node("generate_answer", generate_answer)
    builder.add_node("save_interview", save_interview)
    builder.add_node("write_section", write_section)

    builder.add_edge(START, "ask_question")
    builder.add_edge("ask_question", "search_web")
    builder.add_edge("search_web", "generate_answer")
    builder.add_edge("generate_answer", "save_interview")
    builder.add_edge("save_interview", "write_section")
    builder.add_edge("write_section", END)

    return builder.compile(checkpointer=memory)

class AutonomousReportGenerator:
    def __init__(self,llm):
        """ _summary_
        """
        self.llm = llm
        self.memory = MemorySaver()
        self.tavily_search = TavilySearch()

    def create_analyst(self, state: GenerateAnalystsState):
        """ _summary_
        """
        topic = state["topic"]
        max_analysts = state["max_analysts"]
        human_analyst_feedback = state.get("human_analyst_feedback", "")

        structured_llm = self.llm.with_structured_output(Perspectives)

        system_messages = CREATE_ANALYSTS_PROMPT.format(
            topic=topic,
            max_analysts=max_analysts,
            human_analyst_feedback=human_analyst_feedback
        )

        analysts = structured_llm.invoke([
            SystemMessage(content=CREATE_ANALYSTS_PROMPT),
            HumanMessage(content="Generate the set of analysts.")
        ])
        
        # Write the list of analysts to state
        return{"analysts": analysts.analysts}

    def human_feedback(self):
        """_summary_
        """
        pass

    def write_report(self, state: ResearchGraphState):
        """ _summary_
        """
        sections = state.get("sections", [])
        topic = state.get("topic", "")
        system_message = f"You are compiling a unified research report on: {topic}."
        if not sections:
            sections = ["No sections generated - please verify interview stage."]

        report = self.llm.invoke([
            SystemMessage(content=system_message),
            HumanMessage(content="\n\n".join(sections))
        ])
        return {"content": report.content}


    def write_introduction(self, state: ResearchGraphState):
        """ _summary_
        """
        topic = state["topic"]
        intro = self.llm.invoke([
            SystemMessage(content=f"Write a 100-word markdown introduction for {topic}.")
        ])
        return{"introduction": intro.content}


    def write_conclusion(self, state: ResearchGraphState):
        """_summary_
        """

    def finalize_report(self, state: ResearchGraphState):
        """ _summary_
        """
        pass

    def save_report(self, final_report: str, topic: str, format: str = "docx", save_dir: str = None):
        """ _summary_
        """
        pass

    def _save_as_docx(self, text:str, file_pat:str):
        """_summary_
        """
        pass

    def _save_as_pdf(self, text:str, file_path:str):
        """_summary_
        """
        pass

    def build_graph(self):
        """ _summary_
        """
    
        builder = StateGraph(ResearchGraphState)

        interview_graph = build_interview_graph(self.llm, self.tavily_search)

        def initiate_all_interviews(state: ResearchGraphState):
            topic = state["topic"]
            analysts = state.get("analysts", [])
            if not analysts:
                print("No analysts found - skipping interviews.")
                return END
            # Create one Send() event per analyst
            return [
                Send(
                    "conduct_interview",
                    {
                        "analyst": analyst,
                        "messages": [HumanMessage(content=f"so let's discuss about {topic}.")],
                        "max_num_turns": 2,
                        "context": [],
                        "interview": "",
                        "sections": [],
                    },
                )
                for analyst in analysts
                ]

        # Add nodes
        builder.add_node("create_analyst", self.create_analyst)
        builder.add_node("human_feedback", self.human_feedback)
        builder.add_node("conduct_interview", interview_graph)
        builder.add_node("write_report", self.write_report)
        builder.add_node("write_introduction", self.write_introduction)
        builder.add_node("write_conclusion", self.write_conclusion)
        builder.add_node("finalize_report", self.finalize_report)

        # Edges
        builder.add_edge(START, "create_analyst")
        builder.add_edge("create_analyst", "human_feedback")

        # Map each analyst -> interview graph
        builder.add_conditional_edges("human_feedback", initiate_all_interviews, ["conduct_interview"])

        builder.add_edge("conduct_interview", "write_report")
        builder.add_edge("conduct_interview", "write_introduction")
        builder.add_edge("conduct_interview", "write_conclusion")
        builder.add_edge(
            ["write_report", "write_introduction", "write_conclusion"], "finalize_report"
            )
        builder.add_edge("finalize_report", END)

        return builder.compile(interrupt_before=["human_feedback"], checkpointer=self.memory)

if __name__ == "__main__":
        """ _summary_
        """
        llm = ModelLoader().load_llm()
        #print(llm.invoke("Hello").content)

        reporter = AutonomousReportGenerator(llm)

        graph = reporter.build_graph()

        topic = ""

        thread = {"configurable": {"thread_id": "1"}}

        for _ in graph.stream({"topic": topic, "max_analysts": 3}, thread, stream_mode="values"):
            pass

        state = graph.get_state(thread)

        feedback = input("\n Enter your feedback or press <ENTER> to continue(no feedback): ").strip()

        graph.update_state(thread, {"human_analyst_feedback": feedback}, as_node="human_feedback")

        for _ in graph.stream(None, thread, stream_mode="values"):
            pass

        final_state = graph.get_state(thread)
        final_report = final_state.values.get("final_report")

        if final_report:
            reporter.save_report(final_report, topic, "docx")
            reporter.save_report(final_report, topic, "pdf")
        else:
            print("No Report Content Generated")
