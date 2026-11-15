/**
 * The landing page's hero picture, drawn here as inline SVG: original, flat artwork and no image file.
 *
 * Two unnamed figures stand either side of a job slip that lists, in the system's own words, what an
 * explanation says ("Same trade", "Same area", "Open that week"), joined to it by dotted lines in the two
 * role colours (orange for the worker, blue for the client). The slip is labelled "Example": it is not a
 * real job, worker or client, and the landing page names no one (see app/page.tsx).
 *
 * It is decoration: aria-hidden, no <title>, nothing focusable, and no motion, so there is nothing for
 * prefers-reduced-motion to switch off. Its words stay clear of what the landing tests forbid (digits with a
 * plus, KES, percentages, "score", "best", "search" and the like).
 */

const INK = "#0f172a";
const SKIN_WORKER = "#7a4a2b";
const SKIN_CLIENT = "#a86a3c";

function Check({ y }: { y: number }) {
  return (
    <>
      <circle cx="28" cy={y} r="9" fill="#16a34a" />
      <path d={`M24 ${y}l3 3 6-6`} fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </>
  );
}

export function LandingArt({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 560 400" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="mabati" width="24" height="14" patternUnits="userSpaceOnUse">
          <path d="M0 9 Q6 0 12 9 T24 9" fill="none" stroke="#c2410c" strokeWidth="3" strokeLinecap="round" />
        </pattern>
      </defs>

      {/* ground: a corrugated-iron (mabati) roof edge */}
      <rect x="0" y="352" width="560" height="48" fill="#fff" />
      <rect x="0" y="352" width="560" height="48" fill="url(#mabati)" opacity="0.9" />

      {/* dotted links from each figure to the slip */}
      <path d="M152 196 C170 168 180 160 195 162" fill="none" stroke="#c2410c" strokeWidth="3" strokeDasharray="2 9" strokeLinecap="round" />
      <path d="M412 196 C395 168 385 160 365 162" fill="none" stroke="#0051af" strokeWidth="3" strokeDasharray="2 9" strokeLinecap="round" />

      {/* the job slip */}
      <g transform="translate(195 62)">
        <path
          d="M12 0h146a12 12 0 0 1 12 12v68a12 12 0 0 0 0 24v128a12 12 0 0 1-12 12H12a12 12 0 0 1-12-12V104a12 12 0 0 0 0-24V12A12 12 0 0 1 12 0Z"
          fill="#fff"
          stroke={INK}
          strokeWidth="2.5"
        />
        <rect x="14" y="14" width="142" height="26" rx="4" fill={INK} />
        <text x="26" y="32" fontFamily="ui-monospace, Menlo, monospace" fontSize="13" fontWeight="700" letterSpacing="2" fill="#fff">
          KAZI
        </text>
        <text x="146" y="32" textAnchor="end" fontFamily="ui-monospace, Menlo, monospace" fontSize="12" fontWeight="700" letterSpacing="1.5" fill="#fbbf24">
          EXAMPLE
        </text>
        <g fontFamily="Inter, system-ui, sans-serif" fontSize="15" fontWeight="600" fill={INK}>
          <Check y={68} />
          <text x="46" y="74">Same trade</text>
          <line x1="14" y1="100" x2="156" y2="100" stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 5" />
          <Check y={126} />
          <text x="46" y="132">Same area</text>
          <Check y={158} />
          <text x="46" y="164">Open that week</text>
        </g>
        <rect x="14" y="186" width="142" height="32" rx="6" fill="#eff4ff" stroke="#dce9ff" />
        <text x="85" y="207" textAnchor="middle" fontFamily="Inter, system-ui, sans-serif" fontSize="15" fontWeight="700" fill="#0051af">
          Why this job?
        </text>
      </g>

      {/* the worker: hard hat, orange overalls, a spanner */}
      <ellipse cx="96" cy="350" rx="52" ry="7" fill={INK} opacity="0.12" />
      <rect x="66" y="280" width="20" height="68" rx="8" fill={INK} />
      <rect x="104" y="280" width="20" height="68" rx="8" fill={INK} />
      <rect x="58" y="344" width="32" height="9" rx="4" fill={INK} />
      <rect x="100" y="344" width="32" height="9" rx="4" fill={INK} />
      <rect x="52" y="178" width="86" height="116" rx="26" fill="#c2410c" />
      <rect x="72" y="178" width="46" height="46" rx="6" fill="#9a3412" />
      <rect x="80" y="206" width="30" height="16" rx="3" fill="#7c2d12" />
      <rect x="34" y="188" width="24" height="76" rx="12" fill="#c2410c" transform="rotate(10 46 190)" />
      <rect x="132" y="186" width="24" height="70" rx="12" fill="#c2410c" transform="rotate(-24 144 190)" />
      <circle cx="154" cy="196" r="11" fill="#6f4426" />
      <circle cx="38" cy="262" r="11" fill="#6f4426" />
      <g transform="translate(-124 70) rotate(-10 162 170)">
        <rect x="158" y="136" width="8" height="64" rx="4" fill="#cbd5e1" stroke={INK} strokeWidth="2" />
        <path d="M152 138a12 12 0 1 1 20 0v8h-6v-5a6 6 0 0 0-8 0v5h-6Z" fill="#cbd5e1" stroke={INK} strokeWidth="2" />
      </g>
      <rect x="85" y="150" width="20" height="26" rx="8" fill="#6f4426" />
      <circle cx="95" cy="128" r="32" fill={SKIN_WORKER} />
      <circle cx="84" cy="128" r="3.4" fill={INK} />
      <circle cx="106" cy="128" r="3.4" fill={INK} />
      <path d="M85 142q10 8 20 0" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" />
      <path d="M58 116a37 34 0 0 1 74 0v4H58Z" fill="#f59e0b" stroke={INK} strokeWidth="2.5" />
      <rect x="50" y="116" width="90" height="10" rx="5" fill="#f59e0b" stroke={INK} strokeWidth="2.5" />
      <rect x="88" y="84" width="14" height="14" rx="3" fill="#fbbf24" />

      {/* the client: a headwrap, a blue top, a phone */}
      <g transform="translate(40 0)">
        <ellipse cx="426" cy="350" rx="52" ry="7" fill={INK} opacity="0.12" />
        <path d="M392 262h68l8 86h-84Z" fill={INK} />
        <rect x="384" y="344" width="34" height="9" rx="4" fill={INK} />
        <rect x="438" y="344" width="34" height="9" rx="4" fill={INK} />
        <rect x="380" y="178" width="92" height="112" rx="28" fill="#0051af" />
        <path d="M404 178q22 26 44 0" fill="#eff4ff" />
        <rect x="462" y="186" width="24" height="70" rx="12" fill="#0051af" transform="rotate(-8 474 190)" />
        <rect x="368" y="190" width="24" height="64" rx="12" fill="#0051af" transform="rotate(30 380 194)" />
        <circle cx="372" cy="196" r="11" fill={SKIN_CLIENT} />
        <rect x="352" y="180" width="30" height="46" rx="6" fill={INK} transform="rotate(-18 367 203)" />
        <rect x="356" y="185" width="22" height="34" rx="3" fill="#bfdbfe" transform="rotate(-18 367 203)" />
        <rect x="416" y="150" width="20" height="26" rx="8" fill={SKIN_CLIENT} />
        <circle cx="426" cy="128" r="32" fill={SKIN_CLIENT} />
        <circle cx="415" cy="130" r="3.4" fill={INK} />
        <circle cx="437" cy="130" r="3.4" fill={INK} />
        <path d="M416 143q10 8 20 0" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" />
        <path d="M390 124c-2-30 16-46 38-46s40 16 36 46c-6-14-18-20-36-20s-30 6-38 20Z" fill="#f59e0b" />
        <path d="M394 108c14-10 28-12 44-8" fill="none" stroke="#c2410c" strokeWidth="5" strokeLinecap="round" />
        <circle cx="458" cy="104" r="9" fill="#f59e0b" />
      </g>
    </svg>
  );
}

/** A blueprint grid of dots behind the hero. Hard-edged, so the page stays flat (no gradients). */
export function DotGrid({ className }: { className?: string }) {
  return (
    <svg className={className} width="100%" height="100%" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="11" cy="11" r="1.2" fill="#cddff8" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
    </svg>
  );
}

/** A measuring tape's edge: a tick every 12 px, a longer one every 60 px. */
export function Ruler({ className }: { className?: string }) {
  return (
    <svg className={className} width="100%" height="22" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="ticks" width="60" height="22" patternUnits="userSpaceOnUse">
          {[0, 12, 24, 36, 48].map((x) => (
            <rect key={x} x={x} y="0" width="1.5" height={x === 0 ? 14 : 8} fill="#0f172a" />
          ))}
        </pattern>
      </defs>
      <rect width="100%" height="22" fill="#fde2c4" />
      <rect width="100%" height="22" fill="url(#ticks)" />
      <rect width="100%" height="2" fill="#0f172a" />
    </svg>
  );
}
