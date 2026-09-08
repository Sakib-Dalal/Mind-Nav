import {
  BookOpen,
  Rocket,
  ListChecks,
  Cable,
  Cpu,
  AudioLines,
  BrainCircuit,
  Target,
  MessageCircle,
  Workflow,
  FolderArchive,
  ShieldCheck,
  Wrench,
  Code2,
} from "@lucide/svelte";
export const repository = "https://github.com/Sakib-Dalal/Mind-Nav";
export const groups = [
  {
    title: "GET STARTED",
    items: [
      {
        id: "overview",
        title: "Introduction",
        icon: BookOpen,
        description: "Understand the project and find your way.",
      },
      {
        id: "guide",
        title: "Quick start",
        icon: Rocket,
        description: "Your first session, step by step.",
      },
      {
        id: "requirements",
        title: "Requirements",
        icon: ListChecks,
        description: "Hardware, software, and platform setup.",
      },
    ],
  },
  {
    title: "BUILD & USE",
    items: [
      {
        id: "hardware",
        title: "Hardware & wiring",
        icon: Cable,
        description: "Connection diagrams and the complete pin map.",
      },
      {
        id: "firmware",
        title: "Arduino firmware",
        icon: Cpu,
        description: "Flash the board and understand protocol v2.",
      },
      {
        id: "recording",
        title: "Record EEG",
        icon: AudioLines,
        description: "Capture labeled REST and SELECT sessions.",
      },
      {
        id: "models",
        title: "Train a model",
        icon: BrainCircuit,
        description: "Create, evaluate, and activate a personal model.",
      },
      {
        id: "practice",
        title: "Practice",
        icon: Target,
        description: "Check performance before enabling input.",
      },
      {
        id: "communication",
        title: "Communicate",
        icon: MessageCircle,
        description: "Quick phrases, scanning, and spoken messages.",
      },
    ],
  },
  {
    title: "UNDER THE HOOD",
    items: [
      {
        id: "pipeline",
        title: "Signal pipeline",
        icon: Workflow,
        description: "From ADC samples to a selection edge.",
      },
      {
        id: "data",
        title: "Data & migration",
        icon: FolderArchive,
        description: "Local storage, CSV imports, and legacy models.",
      },
      {
        id: "validation",
        title: "Validation & limits",
        icon: ShieldCheck,
        description: "What has been tested and what remains.",
      },
      {
        id: "troubleshooting",
        title: "Troubleshooting",
        icon: Wrench,
        description: "Diagnose connections, signals, and model issues.",
      },
      {
        id: "development",
        title: "Development",
        icon: Code2,
        description: "Repository structure, builds, and checks.",
      },
    ],
  },
];
export const pages = groups.flatMap((group) =>
  group.items.map((item) => ({ ...item, group: group.title })),
);
