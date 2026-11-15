/**
 * The error banner of a form that submits. When the failure was "no response at all" (a dropped connection),
 * it offers "Try again", which sends the same form data again; for any other error there is nothing to retry,
 * because the server answered and the person has to change something.
 */

type Props = {
  message: string;
  className?: string;
  /** Present only when the last submit got no response. Resubmits the form as it stands. */
  onRetry?: () => void;
  busy?: boolean;
};

export function FormAlert({ message, className = "", onRetry, busy = false }: Props) {
  return (
    <div className={`alert ${className}`.trim()} role="alert">
      <p style={{ margin: 0 }}>{message}</p>
      {onRetry && (
        <button type="button" className="button" style={{ marginTop: 12 }} onClick={onRetry} disabled={busy}>
          {busy ? "Trying again…" : "Try again"}
        </button>
      )}
    </div>
  );
}
