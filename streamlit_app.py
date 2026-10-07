import json
import sys
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.schemas.graph import (  # noqa: E402
    CaseNarrativeInput,
    CreateCaseInput,
    FileEvidenceInput,
    NetworkTrafficInput,
)
from app.services.graph_service import GraphService  # noqa: E402
from app.services.llm_service import LLMExtractorService  # noqa: E402
from app.services.ml_service import MLInferenceService  # noqa: E402


st.set_page_config(page_title="CrimeGraph AI", page_icon="🔎", layout="wide")


@st.cache_resource
def initialize_services():
    GraphService.initialize()
    MLInferenceService.load_models()
    return MLInferenceService.readiness()


def show_action_result(action_name: str, case_id: str):
    result = st.session_state.get("last_action")
    if result and result["action"] == action_name and result["case_id"] == case_id:
        st.success(result["message"])
        st.json(result["result"])


def graph_to_dot(graph):
    shapes = {
        "CrimeCase": "doubleoctagon",
        "Person": "box",
        "Phone": "ellipse",
        "Location": "diamond",
        "IPAddress": "hexagon",
        "EvidenceFile": "note",
    }
    lines = ["digraph Investigation {", "  rankdir=LR;", "  node [style=filled, fillcolor=\"#e9f1fb\"];"]
    for node in graph["nodes"]:
        label = f'{node["label"]}\n({node["type"]})'
        lines.append(
            f'  {json.dumps(node["id"])} '
            f'[label={json.dumps(label)}, shape={shapes.get(node["type"], "ellipse")}];'
        )
    for edge in graph["edges"]:
        lines.append(
            f'  {json.dumps(edge["source"])} -> {json.dumps(edge["target"])} '
            f'[label={json.dumps(edge["relation"])}];'
        )
    lines.append("}")
    return "\n".join(lines)


st.title("CrimeGraph AI")
st.caption("Local Streamlit demo — directly uses the Python services, without HTTP API calls.")
st.warning(
    "Model scores and extracted links are fallible demonstration outputs, not verified evidence or proof."
)

with st.spinner("Loading the local database and model files..."):
    model_status = initialize_services()

with st.sidebar:
    st.header("Investigation case")
    cases = GraphService.list_cases()
    case_ids = [case["case_id"] for case in cases]
    if not case_ids:
        st.error("No cases are available.")
        st.stop()

    pending_case_id = st.session_state.pop("pending_case_id", None)
    if pending_case_id in case_ids:
        st.session_state["selected_case_id"] = pending_case_id

    selected_case_id = st.selectbox(
        "Choose a case",
        case_ids,
        format_func=lambda case_id: next(
            f'{case["title"]} ({case_id})' for case in cases if case["case_id"] == case_id
        ),
        key="selected_case_id",
    )
    selected_case = next(case for case in cases if case["case_id"] == selected_case_id)

    st.subheader("Create a case")
    with st.form("create_case_form"):
        new_case_id = st.text_input("Case ID", placeholder="CASE_DEMO_02")
        new_case_title = st.text_input("Title", placeholder="Synthetic evidence review")
        new_case_description = st.text_area("Description")
        create_case_clicked = st.form_submit_button("Create case")
    if create_case_clicked:
        try:
            payload = CreateCaseInput(
                case_id=new_case_id.strip(),
                title=new_case_title.strip(),
                description=new_case_description.strip(),
            )
            GraphService.create_case(payload.case_id, payload.title, payload.description)
        except (ValidationError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.session_state["pending_case_id"] = payload.case_id
            st.session_state["last_action"] = None
            st.rerun()

    st.divider()
    st.subheader("Local model readiness")
    for model_name, ready in model_status.items():
        (st.success if ready else st.error)(f"{model_name}: {'ready' if ready else 'unavailable'}")

st.subheader(selected_case["title"])
st.caption(selected_case.get("description", ""))
overview_tab, notes_tab, traffic_tab, file_tab = st.tabs(
    ["Case graph", "Analyze notes", "Analyze traffic", "Classify file bytes"]
)

with overview_tab:
    graph = GraphService.get_case_graph(selected_case_id)
    metric_nodes, metric_edges = st.columns(2)
    metric_nodes.metric("Graph entities", graph["total_nodes"])
    metric_edges.metric("Relationships", graph["total_edges"])
    st.graphviz_chart(graph_to_dot(graph), use_container_width=True)
    with st.expander("View graph records"):
        st.subheader("Entities")
        st.dataframe(graph["nodes"], use_container_width=True)
        st.subheader("Relationships")
        st.dataframe(graph["edges"], use_container_width=True)

with notes_tab:
    st.write("Extract entities from fictional case notes with the local pattern extractor.")
    with st.form("notes_form"):
        narrative = st.text_area(
            "Case notes",
            value=(
                "Suspect John Mercer (phone: +44 7911 123456) met Marcus Vance "
                "near Central Station. The server was 198.51.100.22."
            ),
            height=150,
        )
        analyze_notes = st.form_submit_button("Extract and add to graph")
    if analyze_notes:
        try:
            payload = CaseNarrativeInput(
                case_id=selected_case_id,
                case_title=selected_case["title"],
                narrative_text=narrative,
            )
        except ValidationError as exc:
            st.error(str(exc))
        else:
            extracted = LLMExtractorService.extract_locally_from_narrative(
                payload.narrative_text, payload.case_id
            )
            updated_graph = GraphService.add_extracted_entities(payload.case_id, extracted)
            st.session_state["last_action"] = {
                "action": "notes",
                "case_id": selected_case_id,
                "message": (
                    f"Local extraction added/updated entities. Graph now has "
                    f'{len(updated_graph["nodes"])} entities and {len(updated_graph["edges"])} relationships.'
                ),
                "result": extracted,
            }
            st.rerun()
    show_action_result("notes", selected_case_id)

with traffic_tab:
    st.write("Enter one synthetic network flow. The inference service formats it for the model.")
    if not model_status["botnet_cnn_lstm"]:
        st.error("Traffic model files are unavailable; traffic analysis is disabled.")
    with st.form("traffic_form"):
        source_col, destination_col = st.columns(2)
        with source_col:
            src_ip = st.text_input("Source IP", value="192.168.1.105")
        with destination_col:
            dst_ip = st.text_input("Destination IP", value="198.51.100.22")
        flow_col1, flow_col2, flow_col3 = st.columns(3)
        with flow_col1:
            duration = st.number_input("Duration (seconds)", min_value=0.0, value=0.045, step=0.001)
            src_bytes = st.number_input("Source bytes", min_value=0, value=84)
            src_pkts = st.number_input("Source packets", min_value=0, value=2)
        with flow_col2:
            dst_bytes = st.number_input("Destination bytes", min_value=0, value=72)
            dst_pkts = st.number_input("Destination packets", min_value=0, value=1)
            inter_arrival_time = st.number_input(
                "Inter-arrival time (seconds)", min_value=0.0, value=4.82, step=0.01
            )
        with flow_col3:
            protocol = st.selectbox("Protocol", ["TCP", "UDP", "ICMP"])
            is_common_port = st.checkbox("Common port", value=False)
            syn_count = st.number_input("SYN count", min_value=0, value=1)
            fin_count = st.number_input("FIN count", min_value=0, value=0)
            rst_count = st.number_input("RST count", min_value=0, value=0)
        analyze_traffic = st.form_submit_button(
            "Analyze traffic",
            disabled=not model_status["botnet_cnn_lstm"],
        )
    if analyze_traffic:
        try:
            flow = NetworkTrafficInput(
                case_id=selected_case_id,
                src_ip=src_ip.strip(),
                dst_ip=dst_ip.strip(),
                duration=duration,
                src_bytes=src_bytes,
                dst_bytes=dst_bytes,
                src_pkts=src_pkts,
                dst_pkts=dst_pkts,
                is_tcp=int(protocol == "TCP"),
                is_udp=int(protocol == "UDP"),
                is_icmp=int(protocol == "ICMP"),
                is_common_port=int(is_common_port),
                inter_arrival_time=inter_arrival_time,
                syn_count=syn_count,
                fin_count=fin_count,
                rst_count=rst_count,
            )
        except ValidationError as exc:
            st.error(str(exc))
        else:
            result = MLInferenceService.predict_traffic_flow(flow)
            graph = GraphService.add_traffic_result(selected_case_id, result)
            result["total_graph_nodes"] = len(graph["nodes"])
            result["total_graph_edges"] = len(graph["edges"])
            st.session_state["last_action"] = {
                "action": "traffic",
                "case_id": selected_case_id,
                "message": "Traffic analyzed and result added to the case graph.",
                "result": result,
            }
            st.rerun()
    show_action_result("traffic", selected_case_id)

with file_tab:
    st.write("Paste a hexadecimal byte sample to predict its file category.")
    if not model_status["file_classifier_mlp"]:
        st.error("File classifier files are unavailable; file classification is disabled.")
    with st.form("file_form"):
        file_name = st.text_input("Evidence file name", value="recovered_drive_dump.bin")
        hex_content = st.text_area(
            "Hex bytes",
            value="25 50 44 46 2d 31 2e 35 0a 25 c7 ec 8f a2 31 20 30 20 6f 62 6a",
            height=120,
        )
        classify_file = st.form_submit_button(
            "Classify file sample",
            disabled=not model_status["file_classifier_mlp"],
        )
    if classify_file:
        try:
            evidence = FileEvidenceInput(
                case_id=selected_case_id,
                file_name=file_name.strip(),
                hex_content=hex_content.strip(),
            )
        except ValidationError as exc:
            st.error(str(exc))
        else:
            result = MLInferenceService.classify_file_evidence(evidence)
            graph = GraphService.add_file_result(selected_case_id, result)
            result["total_graph_nodes"] = len(graph["nodes"])
            result["total_graph_edges"] = len(graph["edges"])
            st.session_state["last_action"] = {
                "action": "file",
                "case_id": selected_case_id,
                "message": "File sample classified and result added to the case graph.",
                "result": result,
            }
            st.rerun()
    show_action_result("file", selected_case_id)
