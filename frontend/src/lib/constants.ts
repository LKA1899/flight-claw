export const STATUS_OPTIONS = ["PENDING", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "PARTIAL_SUCCESS", "SKIPPED", "CANCEL_REQUESTED", "CANCELLED"];
export const ENABLED_OPTIONS = [
  { value: "true", label: "启用" },
  { value: "false", label: "停用" },
];
export const PLATFORM_OPTIONS = [{ value: "CTRIP", label: "CTRIP" }];
export const STRATEGY_OPTIONS = [
  { value: "direct", label: "直飞" },
  { value: "transfer", label: "中转" },
  { value: "train", label: "接驳" },
  { value: "hidden", label: "甩尾" },
];
