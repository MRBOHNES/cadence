export function Footer() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-x-6 border-t border-line pt-3 text-[12px] text-muted">
      <p>All times IST (Asia/Kolkata)</p>
      <p>
        Built by Bhavanjot Singh ·{" "}
        <a
          href="https://github.com/MRBOHNES/cadence"
          className="inline-flex min-h-[44px] items-center underline underline-offset-2"
        >
          Source on GitHub
        </a>
      </p>
    </footer>
  );
}
