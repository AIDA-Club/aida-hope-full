/** One consistent line-icon set (2px rounded strokes), matched to the reference screenshots. */
import { SVGProps } from "react";

const PATHS: Record<string, JSX.Element> = {
  arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
  chevron: <path d="m9 6 6 6-6 6" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 5 5" /></>,
  sliders: <><path d="M4 8h16M4 16h16" /><circle cx="9" cy="8" r="2.4" fill="currentColor" /><circle cx="15" cy="16" r="2.4" fill="currentColor" /></>,
  question: <><path d="M20 11.5a8.5 8.5 0 0 1-12.4 7.6L3.5 20.5l1.4-4A8.5 8.5 0 1 1 20 11.5Z" /><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6" /><path d="M12 16.6h.01" /></>,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6" /><path d="M12 17h.01" /></>,
  cards: <><rect x="4" y="6.5" width="10" height="14" rx="2" transform="rotate(-10 9 13.5)" /><rect x="9.5" y="3.5" width="10" height="14" rx="2" transform="rotate(10 14.5 10.5)" /></>,
  pencil: <><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z" /><path d="m13.5 6.5 4 4" /></>,
  folder: <path d="M3.5 7.5A2 2 0 0 1 5.5 5.5h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7.5Z" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6" /><path d="M12 7.5h.01" /></>,
  image: <><rect x="3.5" y="4.5" width="17" height="15" rx="2.5" /><circle cx="9" cy="10" r="1.8" /><path d="m4 17 5-4.5 3.5 3 3-2.5 4.5 4" /></>,
  expand: <><path d="M14 4h6v6" /><path d="M20 4l-7 7" /><path d="M10 20H4v-6" /><path d="M4 20l7-7" /></>,
  user: <><circle cx="12" cy="8.5" r="3.8" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
  robot: <><rect x="4" y="7.5" width="16" height="11.5" rx="3.5" /><path d="M12 7.5V4.5" /><circle cx="12" cy="3.8" r="1" /><circle cx="9" cy="13" r="1.3" fill="currentColor" /><circle cx="15" cy="13" r="1.3" fill="currentColor" /><path d="M2 12.5v2.5M22 12.5v2.5" /></>,
  document: <><path d="M7 3.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5Z" /><path d="M9 11h6M9 14.5h6M9 18h4" /></>,
  book: <><path d="M12 6.5C10 5 7 4.5 3.5 5v13c3.5-.5 6.5 0 8.5 1.5 2-1.5 5-2 8.5-1.5V5C17 4.5 14 5 12 6.5Z" /><path d="M12 6.5v13" /></>,
  pin: <><path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11Z" /><circle cx="12" cy="10" r="2.4" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  send: <><path d="M21 3 10 14" /><path d="m21 3-6.5 18-4.5-7-7-4.5L21 3Z" /></>,
  chat: <path d="M20 11.5a8.5 8.5 0 0 1-12.4 7.6L3.5 20.5l1.4-4A8.5 8.5 0 1 1 20 11.5Z" />,
  leaf: <><path d="M5 19c0-9 5-14 15-14 0 10-5 15-14 15" /><path d="M5 19 13 11" /></>,
  cell: <><circle cx="12" cy="12" r="4.5" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" /><circle cx="11" cy="11" r="1" fill="currentColor" /></>,
  microscope: <><path d="M6 20h12" /><path d="M8 20a6 6 0 0 1 9-7" /><path d="m9.5 4.5 3-1.5 3.5 7-3 1.5z" /><path d="M11.5 11.5 13 14.5" /><circle cx="13" cy="15.5" r="1" /></>,
  bars: <><path d="M6 20v-7M12 20V5M18 20v-10" /></>,
  warning: <><path d="M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" /><path d="M12 9.5v4.5" /><path d="M12 17.3h.01" /></>,
  alert: <><circle cx="12" cy="12" r="9" /><path d="M12 7v6" /><path d="M12 16.5h.01" /></>,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  tools: <><path d="M14.5 6.5a4 4 0 0 0 5 5l-9 9a2.1 2.1 0 0 1-3-3Z" /><path d="M4 4l5 5" /><path d="M3 7l4-4" /></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14-4.5L4 9" /><path d="M4 4v5h5" /><path d="M4 13a8 8 0 0 0 14 4.5l2-2.5" /><path d="M20 20v-5h-5" /></>,
  gear: <><circle cx="12" cy="12" r="3" /><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1" /></>,
};

/** Icons that point "forward" and must mirror in right-to-left layouts. */
const DIRECTIONAL = new Set(["arrow", "chevron", "send"]);

export type IconName = keyof typeof PATHS;

interface Props extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
  label?: string;
}

export function Icon({ name, size = 24, label, className = "", ...rest }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`icon${DIRECTIONAL.has(name) ? " icon-dir" : ""} ${className}`}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  );
}
