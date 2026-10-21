/**
 * The API contract, hand-written from docs/api.md.
 *
 * Every field the API can omit is typed `| null`, never optional and never
 * defaulted to 0: `null` means "not assessed" and must reach the UI as such.
 */

export const AVAILABILITY = ["Full-time", "Part-time", "Weekends"] as const;
export type Availability = (typeof AVAILABILITY)[number];

export type Health = { status: string; ready: boolean; candidate_jobs: number };

export type WorkerInput = {
  biography: string;
  skills: string[];
  location: string | null;
  availability: Availability | null;
  rate_expectation: number | null;
};

export type JobInput = {
  title: string;
  description: string;
  required_skills: string[];
  location: string | null;
  availability: Availability | null;
  budget: number | null;
};

/** A worker as the API returns it: `worker_id` is null for a profile that was typed in, not stored. */
export type Worker = WorkerInput & { worker_id: string | null };

export type Job = JobInput & { posting_id: string };

export type NodeRef = { id: string; label: string };
export type GraphNode = NodeRef & { type: "InformalTerm" | "Occupation" | "Skill" | "SkillGroup" };
export type GraphEdge = { source: GraphNode; relation: string; target: GraphNode };

export type Enrichment = { terms: NodeRef[]; occupations: NodeRef[]; unmapped: string[] };

/** How the worker came to have a matched skill. */
export type SkillSource = "listed" | "text" | "informal_term" | "occupation_label";

export type MatchedSkill = {
  skill: string;
  skill_label: string;
  source: SkillSource;
  graph_path: GraphEdge[];
};

export const RULE_CRITERIA = ["skill_overlap", "location", "budget_fit", "availability"] as const;
export type RuleCriterion = (typeof RULE_CRITERIA)[number];

/** A criterion is null when its field is missing on either side; the whole object is null without a rule component. */
export type RuleComponents = Record<RuleCriterion, number | null>;

export type MatchResult = {
  rank: number;
  posting_id: string;
  title: string;
  description: string;
  location: string | null;
  availability: Availability | null;
  budget: number | null;
  scores: { composite: number; rule: number | null; semantic: number | null };
  rule_components: RuleComponents | null;
  matched_skills: MatchedSkill[];
};

export type Recommendation = {
  configuration: string;
  k: number;
  worker: Worker;
  enrichment: Enrichment;
  results: MatchResult[];
  timing_ms: number;
};

export type CreatedWorker = { worker_id: string; worker: Worker; enrichment: Enrichment };

/** A posting's stated skills only: matching never uses skills inferred for a posting. */
export type StatedSkill = { skill: string; skill_label: string; source: "listed" | "text" };

export type JobInterpretation = {
  posting_id: string;
  job: Job;
  interpretation: Enrichment & {
    stated_skills: StatedSkill[];
    worker_pool: { occupation: NodeRef; workers: number }[];
  };
  candidate_jobs: number;
};

export type ApiErrorCode =
  | "invalid_request"
  | "not_found"
  | "method_not_allowed"
  | "not_supported"
  | "not_ready"
  | "internal_error"
  | "network_error";

export type ApiErrorBody = { error: { code: ApiErrorCode; message: string; field?: string } };
