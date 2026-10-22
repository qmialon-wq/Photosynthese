export {};
declare module "vue" {
  export interface GlobalComponents {
    PButton: (typeof import("primevue/button"))["default"];
    PTag: (typeof import("primevue/tag"))["default"];
    PDialog: (typeof import("primevue/dialog"))["default"];
    PInputText: (typeof import("primevue/inputtext"))["default"];
    PProgressBar: (typeof import("primevue/progressbar"))["default"];
    LoadState: (typeof import("./components/LoadState.vue"))["default"];
    StatusBadge: (typeof import("./components/StatusBadge.vue"))["default"];
    TaskPanel: (typeof import("./components/TaskPanel.vue"))["default"];
    MetricsPanel: (typeof import("./components/MetricsPanel.vue"))["default"];
  }
}
