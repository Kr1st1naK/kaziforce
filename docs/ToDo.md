# PHASE 1 — Data-source decision
Now
Meet Webmasters.
Determine exactly what data they can provide.
Establish whether research use is authorised.
Record what fields are available.
Don't make the project dependent on them.

# PHASE 2 — Job corpus
Retain Job Skill Set as a supplementary job corpus.
Inspect/select relevant job postings.
Clean job descriptions.
Normalize extracted skills.
Map relevant skills to your KG where appropriate.

# PHASE 3 — Kenyan occupational vocabulary
Identify candidate informal occupational areas.
Reduce them to approximately 15–20 manageable areas.
Collect candidate informal terms.
Validate each term.
Map informal term → formal occupation.
Map formal occupation → ESCO.
Map occupation → relevant skills.
Freeze the vocabulary.

# PHASE 4 — Knowledge graph
Create occupation entities.
Create skill entities.
Create informal-term entities.
Create relationships between them.
Connect jobs to occupations/skills.
Connect workers to occupations/skills.

# PHASE 5 — Synthetic workers
Generate workers from the frozen occupational vocabulary.
Vary how they describe themselves.
Include formal English descriptions.
Include informal terminology.
Include potentially mixed/variant descriptions.
Add relevant matching attributes such as location, availability and rate where your experimental design requires them.

# PHASE 6 — Ground truth
Create job requirements independently.
Define worker capabilities independently.
Determine expected worker–job relevance.
Freeze the relevance labels.
Only then run your recommender.

#  PHASE 7 — Evaluation
Run keyword baseline.
Run rule-based configuration.
Run semantic configuration.
Run hybrid without KG, if implemented.
Run KG-enhanced hybrid.
Compare Precision@K/MRR and any additional implemented metrics.
Run the Kenyan terminology experiment.
Run cold-start experiment.
Evaluate explanation traceability.
