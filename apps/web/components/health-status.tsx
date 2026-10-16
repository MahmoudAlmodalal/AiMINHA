"use client";

import { useState } from "react";
import { getHealth } from "@minhaai/contracts";

export function HealthStatus({ locale }: { locale: "ar" | "en" }) {
  const [state, setState] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const ar = locale === "ar";
  const messages = ar
    ? { idle: "يمكنك التحقق من الاتصال.", loading: "جارٍ التحقق…", ok: "الاتصال متاح.", error: "تعذّر الاتصال. حاول مجددًا." }
    : { idle: "You can check the connection.", loading: "Checking…", ok: "Connection available.", error: "Could not connect. Try again." };

  async function check() {
    setState("loading");
    try {
      await getHealth();
      setState("ok");
    } catch {
      setState("error");
    }
  }

  return (
    <section aria-label={ar ? "الاتصال" : "Connection"}>
      <button onClick={check} disabled={state === "loading"}>
        {ar ? "تحقّق من الاتصال" : "Check connection"}
      </button>
      <p role="status" aria-live="polite">{messages[state]}</p>
    </section>
  );
}
