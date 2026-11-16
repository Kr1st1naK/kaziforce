import { useEffect, useRef } from "react";

/**
 * Calls `reset` when the page is navigated away from (or unmounted).
 *
 * Next keeps a route mounted but hidden, in an Activity, so that going back is instant. State survives
 * that, including a button's "busy" flag. A form that goes busy on a successful submit and then navigates
 * away would come back, on the next visit, still saying "Signing in…" with its fields disabled and nothing
 * submitted. React tears the effects of a hidden Activity down, so a cleanup here runs at exactly that moment.
 */
export function useIdleWhenHidden(reset: () => void): void {
  const latest = useRef(reset);
  useEffect(() => {
    latest.current = reset;
  });
  useEffect(() => () => latest.current(), []);
}
