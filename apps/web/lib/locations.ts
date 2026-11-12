/**
 * Suggested locations: the places used by the synthetic dataset
 * (LOCATIONS in apps/api/src/kaziforce_api/data/synthetic.py).
 *
 * In the interface this is a closed list: "Where do you work?" and "Where is the
 * job?" are <select> fields, so a place not listed here cannot be chosen (system
 * test record, T-08). The API itself accepts any text, and the rule-based location
 * criterion compares the town before " - " when the two differ
 * (docs/scoring-policy.md §1).
 */

export const SUGGESTED_LOCATIONS = [
  "Nairobi - Kasarani",
  "Nairobi - Embakasi",
  "Nairobi - Westlands",
  "Nairobi - Kibera",
  "Nairobi - Kawangware",
  "Nairobi - Githurai",
  "Nairobi - Umoja",
  "Nairobi - Rongai",
  "Mombasa - Likoni",
  "Mombasa - Nyali",
  "Kisumu",
  "Nakuru",
  "Eldoret",
  "Thika",
  "Machakos",
  "Kitengela",
  "Ruiru",
  "Nyeri",
  "Kakamega",
  "Meru",
] as const;
