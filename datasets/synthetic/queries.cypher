// CrimeGraph demo queries (run in Neo4j Browser after load_to_neo4j.py)

// 1. Everything in one case: incidents, where they happened, and the evidence
MATCH (c:Case {id:'C001'})<-[:PART_OF]-(i:Incident)-[:OCCURRED_AT]->(l:Location)
OPTIONAL MATCH (e:Evidence)-[:SUPPORTS]->(i)
RETURN c, i, l, e;

// 2. People who share a device (possible shared-use link)
MATCH (a:Person)-[:USES]->(d:Device)<-[:USES]-(b:Person)
WHERE a.id < b.id
RETURN a.name AS person_a, b.name AS person_b, d.name AS shared_device;

// 3. Connection path between two people via calls, money, devices or known associations
MATCH p = shortestPath((a:Person {id:'P001'})-[:CONTACTED|USES|OWNS|TRANSFERRED_TO|ASSOCIATED_WITH*..8]-(b:Person {id:'P011'}))
RETURN p;

// 4. Hidden link between two cases: money moving from the robbery ring into the fraud ring
MATCH (p:Person)-[:OWNS]->(:Account)-[t:TRANSFERRED_TO]->(:Account)<-[:OWNS]-(q:Person)
RETURN p.name AS sender, q.name AS receiver, t.amount_inr AS amount, t.timestamp AS at
ORDER BY at;

// 5. Mule pattern: accounts receiving money from 2+ different accounts
MATCH (s:Account)-[t:TRANSFERRED_TO]->(m:Account)
WITH m, count(DISTINCT s) AS senders, sum(t.amount_inr) AS total
WHERE senders >= 2
MATCH (h:Person)-[:OWNS]->(m)
RETURN h.name AS holder, m.name AS account, senders, total ORDER BY total DESC;

// 6. Follow the money from a victim's account to the ATM where cash came out
MATCH p = (v:Account {id:'AC013'})-[:TRANSFERRED_TO*1..4]->(:Account)-[:WITHDRAWN_AT]->(l:Location)
RETURN p;

// 7. Calls between devices in the 48 hours before an incident
MATCH (i:Incident {id:'I001'})
MATCH (a:Device)-[c:CALLED]->(b:Device)
WHERE c.timestamp >= i.datetime - duration('PT48H') AND c.timestamp <= i.datetime
RETURN a.name AS caller, b.name AS callee, c.timestamp AS at, c.duration_sec AS seconds
ORDER BY at;

// 8. Devices from different incidents talking to the same flagged IP address
MATCH (d:Device)-[e:CONNECTED_TO]->(ip:IPAddress)
WHERE e.label STARTS WITH 'Malicious'
RETURN ip.name AS ip, collect(DISTINCT d.name) AS devices, count(e) AS events;

// 9. Provenance: which document says a relationship exists?
MATCH (a:Entity)-[r]->(b:Entity)
WHERE r.source_doc IS NOT NULL AND a.id = 'P002'
RETURN a.name, type(r) AS relationship, b.name, r.source_doc;
