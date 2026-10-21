/**
 * Why a matched skill counted, from `source` (docs/api.md).
 *
 * Each source gets its own words and its own icon, never colour alone. An
 * inferred skill names the term or occupation it came from, so "inferred
 * because you described yourself as a fundi wa umeme" reads differently from
 * "you listed this skill". An unrecognised source falls back to a neutral
 * badge rather than breaking the page.
 */

import type { MatchedSkill, SkillSource } from "@/lib/types";
import styles from "./SkillBadge.module.css";

const DESCRIPTION: Record<SkillSource, { icon: string; text: (origin: string | null) => string }> = {
  listed: { icon: "✓", text: () => "listed by you" },
  text: { icon: "“”", text: () => "your own words" },
  informal_term: { icon: "→", text: (origin) => (origin ? `inferred via ${origin}` : "inferred from your wording") },
  occupation_label: {
    icon: "→",
    text: (origin) => (origin ? `inferred via occupation ${origin}` : "inferred from your occupation"),
  },
};

/** The node an inferred skill was reached from: the first node of its graph path. */
export function originLabel(skill: MatchedSkill): string | null {
  return skill.graph_path[0]?.source.label ?? null;
}

export function SkillBadge({ skill }: { skill: MatchedSkill }) {
  const description = DESCRIPTION[skill.source];
  if (!description) {
    return (
      <span className={`${styles.badge} ${styles.unknown}`}>
        <span>matched</span>
      </span>
    );
  }
  const path = skill.graph_path.map((edge) => `${edge.source.label} → ${edge.target.label}`).join(", ");
  return (
    <span className={`${styles.badge} ${styles[skill.source]}`} title={path || undefined}>
      <i className={styles.icon} aria-hidden="true">
        {description.icon}
      </i>
      <span>{description.text(originLabel(skill))}</span>
    </span>
  );
}

export function MatchedSkillList({ skills, limit }: { skills: MatchedSkill[]; limit?: number }) {
  const shown = limit ? skills.slice(0, limit) : skills;
  const hidden = skills.length - shown.length;
  return (
    <ul className={styles.list}>
      {shown.map((skill) => (
        <li key={skill.skill} className={styles.skill}>
          <span className={styles.label}>{skill.skill_label}</span>
          <SkillBadge skill={skill} />
        </li>
      ))}
      {hidden > 0 && <li className={styles.more}>and {hidden} more</li>}
    </ul>
  );
}
