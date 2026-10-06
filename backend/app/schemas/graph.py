# ==============================================================================
# CrimeGraph AI - Pydantic Schemas (POLE & Graph Data Models)
# ==============================================================================
# Implements the standard UK / Interpol POLE (Person, Object, Location, Event)
# schema for digital criminal investigation networks.

import ipaddress
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator

# --- Graph Node & Edge Models (Cytoscape.js compatible) ---

class GraphNode(BaseModel):
    id: str = Field(..., description="Unique entity identifier (e.g. PER_001, IP_192.168.1.5)")
    label: str = Field(..., description="Human-readable display name")
    type: str = Field(..., description="Entity type: Person, Phone, Location, CrimeCase, IPAddress, EvidenceFile")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")

class GraphEdge(BaseModel):
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node id")
    target: str = Field(..., description="Target node id")
    relation: str = Field(..., description="Relationship label: COMMUNICATED_WITH, INVOLVED_IN, ACCESSED_IP, etc.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence confidence score (0.0 to 1.0)")
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphResponse(BaseModel):
    case_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int

# --- Input Payloads ---

class CreateCaseInput(BaseModel):
    case_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)

class CaseNarrativeInput(BaseModel):
    case_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    case_title: str = Field(..., min_length=2, max_length=120)
    narrative_text: str = Field(
        ..., min_length=10, max_length=20000,
        description="Police FIR or investigator case notes containing suspect names, phones, and events",
        example="On 12-09-2026, suspect John Mercer (phone: +44 7911 123456) met accomplice Marcus Vance at Central Station. They transferred illicit cryptocurrency to server 198.51.100.22."
    )

class NetworkTrafficInput(BaseModel):
    case_id: str = Field(default="CASE_2026_094", min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    src_ip: str = Field(..., example="192.168.1.105")
    dst_ip: str = Field(..., example="198.51.100.22")
    duration: float = Field(..., ge=0, le=86400, example=0.045)
    src_bytes: int = Field(..., ge=0, example=84)
    dst_bytes: int = Field(..., ge=0, example=72)
    src_pkts: int = Field(..., ge=0, example=2)
    dst_pkts: int = Field(..., ge=0, example=1)
    is_tcp: int = Field(default=1, ge=0, le=1)
    is_udp: int = Field(default=0, ge=0, le=1)
    is_icmp: int = Field(default=0, ge=0, le=1)
    is_common_port: int = Field(default=0, ge=0, le=1)
    inter_arrival_time: float = Field(default=4.82, ge=0)
    syn_count: int = Field(default=1, ge=0)
    fin_count: int = Field(default=0, ge=0)
    rst_count: int = Field(default=0, ge=0)

    @field_validator("src_ip", "dst_ip")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise ValueError("IP address must be a valid IPv4 or IPv6 address") from exc

class FileEvidenceInput(BaseModel):
    case_id: str = Field(default="CASE_2026_094", min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    file_name: str = Field(..., min_length=1, max_length=255, example="carved_evidence_004.bin")
    hex_content: str = Field(
        ..., min_length=2, max_length=20000,
        description="Space-separated hex byte stream or header chunk",
        example="25 50 44 46 2d 31 2e 35 0a 25 c7 ec 8f a2 31 20 30 20 6f 62 6a"
    )

    @field_validator("hex_content")
    @classmethod
    def validate_hex_content(cls, value: str) -> str:
        try:
            decoded = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("hex_content must contain valid hexadecimal bytes") from exc
        if not decoded:
            raise ValueError("hex_content must contain at least one byte")
        return value
