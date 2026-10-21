/**
 * A matched skill's graph path as a chain of labelled nodes (wireframe 04).
 *
 * Relations are shown in words, with the graph's own name as a tooltip. The
 * last hop, "required by <job>", belongs to the view rather than the graph:
 * the posting is not a node, so it is marked as such.
 */

import type { GraphEdge, MatchedSkill } from "@/lib/types";
import styles from "./GraphPath.module.css";

const RELATION_WORDS: Record<string, string> = {
  MAPS_TO: "maps to",
  HAS_ESSENTIAL_SKILL: "has essential skill",
  HAS_OPTIONAL_SKILL: "has optional skill",
  TYPE_OF: "is a type of",
};

const NODE_KIND: Record<string, string> = {
  InformalTerm: "your wording",
  Occupation: "ESCO occupation",
  Skill: "ESCO skill",
  SkillGroup: "ESCO skill group",
};

function Node({ label, kind }: { label: string; kind: string }) {
  return (
    <span className={styles.node}>
      {label}
      <span className={styles.kind}>{NODE_KIND[kind] ?? kind}</span>
    </span>
  );
}

function Arrow({ relation }: { relation: string }) {
  return (
    <span className={styles.arrow} title={relation}>
      —{RELATION_WORDS[relation] ?? relation.toLowerCase().replace(/_/g, " ")}→
    </span>
  );
}

export function GraphPath({ skill, jobTitle }: { skill: MatchedSkill; jobTitle: string }) {
  if (skill.graph_path.length === 0) {
    return (
      <p className={styles.direct}>
        You named this skill yourself, so no step through the knowledge graph was needed.{" "}
        <span className={styles.kind}>{skill.source === "listed" ? "recognised ESCO skill" : "your own words"}</span>
      </p>
    );
  }
  const edges: GraphEdge[] = skill.graph_path;
  return (
    <div className={styles.path}>
      <Node label={edges[0].source.label} kind={edges[0].source.type} />
      {edges.map((edge) => (
        <span key={`${edge.source.id}-${edge.relation}-${edge.target.id}`} className={styles.step}>
          <Arrow relation={edge.relation} />
          <Node label={edge.target.label} kind={edge.target.type} />
        </span>
      ))}
      <span className={styles.step}>
        <span className={styles.arrow}>—required by→</span>
        <span className={styles.node}>
          {jobTitle}
          <span className={styles.kind}>this job</span>
        </span>
      </span>
    </div>
  );
}
