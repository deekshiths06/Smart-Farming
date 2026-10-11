export type ActionPriority = "high" | "medium" | "low";

export type ActionCategory = "information" | "soil" | "water" | "weather" | "crop";

export type ActionGroup = "do_first" | "do_next" | "check_later";

export interface ActionRead {
  id: number;
  action_key: string;
  category: string;
  group_key: string;
  title: string;
  explanation: string;
  priority: ActionPriority | null;
  timing: string | null;
  reason: string;
  source: string;
  steps: string[] | null;
  materials: string[] | null;
  check_first: string[] | null;
  avoid: string[] | null;
  done_when: string | null;
  details: Record<string, unknown> | null;
  completed: boolean;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActionPlanRead {
  field_id: number;
  field_name: string;
  planner_version: string;
  has_assessment: boolean;
  assessment_at: string | null;
  top_crop: string | null;
  updated_at: string | null;
  actions: ActionRead[];
  disclaimer: string;
}

export const ACTION_GROUP_ORDER: ActionGroup[] = ["do_first", "do_next", "check_later"];

export const ACTION_GROUP_LABELS: Record<ActionGroup, string> = {
  do_first: "Do First",
  do_next: "Do Next",
  check_later: "Check Later",
};

export const ACTION_GROUP_HINTS: Record<ActionGroup, string> = {
  do_first: "The most important things to do now.",
  do_next: "Important, but not urgent. Do these soon.",
  check_later: "Good to look at when you have time.",
};
