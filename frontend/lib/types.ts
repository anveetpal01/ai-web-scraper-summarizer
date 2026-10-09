export type SummarizeResponse = {
  url: string;
  title: string;
  summary: string;
  keyPoints: string[];
  wordCount: number;
  truncated: boolean;
};

export type ErrorResponse = {
  error: string;
};
