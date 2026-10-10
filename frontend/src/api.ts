/** Typed calls to the Python API (api/main.py). Errors carry a translation key. */
export type ClassName = "normal" | "benign" | "malignant";
export const CLASSES: ClassName[] = ["normal", "benign", "malignant"];

export class ApiError extends Error {
  constructor(public code: string, public status: number, public extra: Record<string, unknown> = {}) {
    super(code);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
      ...init,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("error_offline", 0);
  }
  if (!response.ok) {
    let code = response.status === 502 || response.status === 504 ? "error_offline" : "error_generic";
    let extra: Record<string, unknown> = {};
    try {
      const body = await response.json();
      if (body?.detail?.code) {
        code = body.detail.code;
        extra = body.detail;
      }
    } catch {
      /* not JSON: keep the generic code */
    }
    throw new ApiError(code, response.status, extra);
  }
  return response.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown = {}, signal?: AbortSignal) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body), signal });

// ---- Challenge
export type Phase = "choose" | "ai" | "truth" | "end";
export interface RoundCase {
  card: number;
  image: string;
  ai_pred?: ClassName;
  ai_probs?: Record<ClassName, number>;
  ai_correct?: boolean;
  heatmap?: string;
  truth?: ClassName;
  overlay?: string;
  outcome_key?: string;
  explanation_key?: string;
  explanation_percent?: number;
  overlap_key?: string | null;
}
export interface Round {
  total: number;
  index: number;
  phase: Phase;
  answer: ClassName | null;
  score: { you: number; ai: number; played: number };
  steps: Array<"done" | "current" | "todo">;
  case?: RoundCase;
}
export interface BoothScores { n: number; right: number; test_right: number; test_n: number; test_percent: number }
export interface ChallengeInfo { round_size: number; n_cards: number; scores: BoothScores | null }
export interface Folder {
  number: number; id: string; card: number | null; ai_pred: ClassName; truth: ClassName; percent: number;
  title_key: string; text_key: string; overlay: string;
}
type RoundReply = { round: Round | null };

export const challenge = {
  info: () => request<ChallengeInfo>("/api/challenge/info"),
  folders: () => request<Folder[]>("/api/challenge/folders"),
  round: () => request<RoundReply>("/api/challenge/round"),
  start: (card?: string) => post<RoundReply>("/api/challenge/start", card === undefined ? {} : { card }),
  pick: (answer: ClassName) => post<RoundReply>("/api/challenge/pick", { answer }),
  revealAi: () => post<RoundReply>("/api/challenge/reveal-ai"),
  revealTruth: () => post<RoundReply>("/api/challenge/reveal-truth"),
  next: () => post<RoundReply>("/api/challenge/next"),
  end: () => post<RoundReply>("/api/challenge/end"),
};

// ---- Tweak the Tumor
export interface Feature { name: string; key: string | null; min: number; max: number; median: number }
export interface TweakModel {
  available: boolean;
  default_threshold?: number;
  slide?: boolean;
  features?: Feature[];
  presets?: { benign: number[]; malignant: number[] };
}
export interface Prediction {
  malignant: number; benign: number; threshold: number; prediction: "benign" | "malignant"; confidence: number;
}
export const tweak = {
  model: () => request<TweakModel>("/api/tweak/model"),
  predict: (values: number[], threshold: number, signal?: AbortSignal) =>
    post<Prediction>("/api/tweak/predict", { values, threshold }, signal),
  slideUrl: (values: number[]) => `/api/tweak/slide?values=${values.map((v) => v.toString()).join(",")}`,
};

// ---- Ask AIDA
export interface ChatEntry { role: "user" | "assistant" | "notice" | "topic"; html: string; topic?: string }
export interface ChatState { transcript: ChatEntry[]; turns_left: number; max_chars: number; live: boolean }
export const askAida = {
  state: () => request<ChatState>("/api/chat"),
  topic: (topic: string, lang: string) => post<ChatState>("/api/chat/topic", { topic, lang }),
  send: (question: string, lang: string) => post<ChatState>("/api/chat/message", { question, lang }),
  reset: () => post<ChatState>("/api/chat/reset"),
};

// ---- About
export interface About {
  n_test: number; accuracy: number; caught: number; missed: number; malignant_total: number; false_alarms: number;
  split_sizes: { train: number; val: number; test: number };
  test_counts: Record<ClassName, number> | null;
  confusion_matrix: { rows_truth_cols_pred: ClassName[]; matrix: number[][] };
  booth_set: BoothScores | null;
  images: Partial<Record<"original" | "heatmap" | "confusion-matrix", string>>;
}
export const aboutApi = { get: () => request<About>("/api/about") };
export const homeApi = { get: () => request<{ cards: string[] }>("/api/home") };

export const translationsFor = (lang: string) => request<Record<string, string>>(`/api/i18n/${lang}`);
