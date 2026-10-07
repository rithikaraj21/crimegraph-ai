# ==============================================================================
# CrimeGraph AI - LLM Entity & Relationship Extractor Service (Paper 1 & 2)
# ==============================================================================
# Extracts POLE (Person, Object, Location, Event) entities and relationships
# from unstructured police FIRs and investigative narrative reports.
# Uses Google Gemini 2.0 Flash API with structured JSON output, with a reliable
# rule-based fallback regex engine so the app works seamlessly even without an API key!

import re
import json
import logging
import ipaddress
import requests
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMExtractorService:
    """
    Extracts structured graph entities and relationships from narrative case text.
    """

    @classmethod
    def extract_from_narrative(cls, narrative_text: str, case_id: str) -> Dict[str, Any]:
        """
        Main extraction entrypoint: Calls Gemini API if key is present,
        otherwise uses forensic NER regex parser.
        """
        if settings.GEMINI_API_KEY:
            try:
                extracted = cls._call_gemini_api(narrative_text, case_id)
                extracted["extractor"] = "Gemini"
                return extracted
            except Exception as e:
                logger.warning(f"[-] Gemini API call failed ({e}). Falling back to NLP pattern extractor.")

        extracted = cls._fallback_pattern_extractor(narrative_text, case_id)
        extracted["extractor"] = "Local pattern extractor"
        return extracted

    @classmethod
    def extract_locally_from_narrative(cls, narrative_text: str, case_id: str) -> Dict[str, Any]:
        """Extracts entities with local rules without making external API requests."""
        extracted = cls._fallback_pattern_extractor(narrative_text, case_id)
        extracted["extractor"] = "Local pattern extractor"
        return extracted

    @classmethod
    def _call_gemini_api(cls, narrative: str, case_id: str) -> Dict[str, Any]:
        """
        Invokes Gemini 2.0 Flash REST API with JSON schema enforcement.
        """
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"

        prompt = f"""
        You are an expert Digital Forensics & Criminal Intelligence Analyst.
        Extract all POLE entities (Person, Phone, Location, IPAddress, Account, CrimeEvent) and their
        direct relationships from this case narrative into a strict JSON format.

        Case ID: {case_id}
        Narrative:
        \"\"\"{narrative}\"\"\"

        Return ONLY a raw JSON object with this exact structure:
        {{
            "nodes": [
                {{"id": "PER_1", "label": "Full Name", "type": "Person", "properties": {{"role": "Suspect / Witness"}}}},
                {{"id": "PHO_1", "label": "+4412345678", "type": "Phone", "properties": {{}}}},
                {{"id": "LOC_1", "label": "Location Name", "type": "Location", "properties": {{}}}},
                {{"id": "IP_1", "label": "192.168.1.1", "type": "IPAddress", "properties": {{}}}}
            ],
            "relationships": [
                {{"source": "PER_1", "target": "PHO_1", "relation": "OWNS_PHONE", "confidence": 0.95}},
                {{"source": "PER_1", "target": "LOC_1", "relation": "VISITED", "confidence": 0.90}}
            ]
        }}
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        resp = requests.post(endpoint, json=payload, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
            extracted = json.loads(raw_json)
            if not isinstance(extracted, dict):
                raise ValueError("Gemini response must be a JSON object.")
            nodes = extracted.get("nodes")
            relationships = extracted.get("relationships")
            if not isinstance(nodes, list) or not isinstance(relationships, list):
                raise ValueError("Gemini response must contain node and relationship lists.")

            for node in nodes:
                if not isinstance(node, dict) or not all(
                    isinstance(node.get(field), str) and node[field].strip()
                    for field in ("id", "label", "type")
                ):
                    raise ValueError("Gemini returned an invalid graph node.")
                if not isinstance(node.get("properties", {}), dict):
                    raise ValueError("Gemini returned invalid node properties.")
            for relationship in relationships:
                if not isinstance(relationship, dict) or not all(
                    isinstance(relationship.get(field), str) and relationship[field].strip()
                    for field in ("source", "target", "relation")
                ):
                    raise ValueError("Gemini returned an invalid graph relationship.")
                confidence = relationship.get("confidence", 1.0)
                if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                    raise ValueError("Gemini returned an invalid relationship confidence.")
            return {"nodes": nodes, "relationships": relationships}
        else:
            raise RuntimeError(f"Gemini API returned status code {resp.status_code}: {resp.text}")

    @classmethod
    def _fallback_pattern_extractor(cls, narrative: str, case_id: str) -> Dict[str, Any]:
        """
        High-precision rule-based Named Entity Recognition (NER) fallback.
        Ensures 100% reliable local demonstrations without internet/API latency.
        """
        nodes = []
        relationships = []
        # 1. Base Case Node
        nodes.append({
            "id": case_id,
            "label": f"Investigation {case_id}",
            "type": "CrimeCase",
            "properties": {"status": "ACTIVE_INVESTIGATION"}
        })

        # 2. Extract phone numbers in narrative order and skip duplicate mentions.
        phone_matches = re.findall(r'(\+?\d{1,4}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4})', narrative)
        phones = list(dict.fromkeys(phone_matches))
        for i, phone in enumerate(phones):
            clean_phone = phone.strip()
            if len(clean_phone) >= 8:
                pid = f"PHO_{i+1:02d}"
                nodes.append({
                    "id": pid,
                    "label": clean_phone,
                    "type": "Phone",
                    "properties": {"number": clean_phone}
                })
                relationships.append({
                    "source": case_id,
                    "target": pid,
                    "relation": "EVIDENCE_IN_CASE",
                    "confidence": 1.0
                })

        # 3. Extract IP Addresses
        ip_matches = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', narrative)
        ips = []
        for ip in dict.fromkeys(ip_matches):
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue
            ips.append(ip)
        for i, ip in enumerate(ips):
            ipid = f"IP_{i+1:02d}"
            nodes.append({
                "id": ipid,
                "label": ip,
                "type": "IPAddress",
                "properties": {"ip": ip}
            })
            relationships.append({
                "source": case_id,
                "target": ipid,
                "relation": "IDENTIFIED_NETWORK_HOST",
                "confidence": 0.95
            })

        # 4. Extract Suspect Names (Capitalized Person Entities like John Doe, Marcus Vance)
        person_matches = re.finditer(
            r'\b(?:(?i:suspect|accomplice|victim|witness|informant)\s+)?([A-Z][a-z]+ [A-Z][a-z]+)\b',
            narrative,
        )
        excluded_names = {"Central Station", "Crime Graph", "Operation Blackout", "United Kingdom"}
        seen_names = set()
        person_index = 0
        for match in person_matches:
            name = match.group(1)
            if (
                name in excluded_names
                or name.casefold().endswith((" station", " street", " road", " avenue", " airport", " bank", " harbor"))
                or name.casefold() in seen_names
            ):
                continue
            seen_names.add(name.casefold())
            person_index += 1
            per_id = f"PER_{person_index:02d}"
            preceding_context = narrative[max(0, match.start() - 20):match.start()]
            role_match = re.search(r'\b(suspect|accomplice|victim|witness|informant)\s+$', preceding_context, flags=re.IGNORECASE)
            role = role_match.group(1) if role_match else None
            nodes.append({
                "id": per_id,
                "label": name,
                "type": "Person",
                "properties": {
                    "full_name": name,
                    "mention_context": role.lower() if role else "person mentioned in narrative",
                }
            })
            relationships.append({
                "source": per_id,
                "target": case_id,
                "relation": "MENTIONED_IN_CASE",
                "confidence": 0.92
            })

        # 5. Extract Key Locations
        location_keywords = re.findall(r'\b(?:at|near|in|outside)\s+([A-Z][a-zA-Z\s]+?(?:Station|Street|Road|Avenue|Airport|Bank|Harbor))\b', narrative)
        for i, loc in enumerate(dict.fromkeys(location_keywords)):
            loc_id = f"LOC_{i+1:02d}"
            nodes.append({
                "id": loc_id,
                "label": loc.strip(),
                "type": "Location",
                "properties": {"address": loc.strip()}
            })
            relationships.append({
                "source": case_id,
                "target": loc_id,
                "relation": "CRIME_SCENE_LOCATION",
                "confidence": 0.90
            })

        return {"nodes": nodes, "relationships": relationships}
