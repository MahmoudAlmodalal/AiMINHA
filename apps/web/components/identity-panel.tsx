"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession, type Session } from "@minhaai/contracts";

type Mode = "login" | "signup" | "verify" | "resend" | "resetRequest" | "reset" | "recovery" | "restore";
type Disclosure = { id: string; version: number; purpose: string; disclosure: string; available: boolean };
const client = createHealthClient();

export function IdentityPanel({ locale }: { locale: "ar" | "en" }) {
  const ar = locale === "ar";
  const [mode, setMode] = useState<Mode>("login");
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [token, setToken] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [disclosures, setDisclosures] = useState<Disclosure[]>([]);
  const [impact, setImpact] = useState<{ recovery_days: number; recovery_timezone: string; available: boolean } | null>(null);
  const callbackStarted = useRef(false);
  const labels: Record<Mode, string> = ar ? {
    login: "تسجيل الدخول", signup: "إنشاء حساب بالغ", verify: "تأكيد البريد", resend: "إعادة طلب رمز التأكيد",
    resetRequest: "طلب استعادة كلمة المرور", reset: "تغيير كلمة المرور",
    recovery: "طلب استعادة الحساب المحذوف", restore: "استعادة الحساب",
  } : {
    login: "Sign in", signup: "Create an adult account", verify: "Verify email", resend: "Resend verification code",
    resetRequest: "Request password reset", reset: "Reset password",
    recovery: "Request deleted account recovery", restore: "Restore account",
  };

  function errorMessage(code?: string) {
    const messages: Record<string, [string, string]> = {
      ADULT_REQUIRED: ["يجب أن يكون عمرك 18 عامًا على الأقل.", "You must be at least 18."],
      INVALID_CREDENTIALS: ["تعذّر الدخول. تحقق من بياناتك وتأكيد بريدك.", "Sign-in failed. Check your credentials and email verification."],
      PASSWORD_POLICY: ["اختر عبارة مرور قوية من 12 حرفًا على الأقل.", "Choose a strong passphrase of at least 12 characters."],
      GOOGLE_UNAVAILABLE: ["ربط Google غير متاح حاليًا.", "Google account linking is not currently available."],
      LEGAL_RETENTION_UNAVAILABLE: ["الحذف غير متاح لحين اعتماد سياسة الاحتفاظ.", "Deletion is unavailable until the retention policy is approved."],
      RESTORATION_EXPIRED: ["الاستعادة غير متاحة؛ قد تكون المهلة انتهت.", "Restoration is unavailable; the recovery period may have expired."],
      STALE_CONSENT: ["تغيّرت حالة الموافقة. راجعها وحاول مجددًا.", "Consent changed. Review it and try again."],
      IMPACT_REVIEW_REQUIRED: ["راجع مهلة الحذف الحالية قبل التأكيد.", "Review the current deletion period before confirming."],
      RATE_LIMITED: ["محاولات كثيرة. حاول لاحقًا.", "Too many attempts. Try later."],
    };
    return messages[code ?? ""]?.[ar ? 0 : 1] ?? (ar ? "تعذّر إتمام الطلب. تحقق من البيانات والرمز وحاول مجددًا." : "The request could not be completed. Check the details/code and try again.");
  }

  async function headers() {
    return { "X-CSRFToken": await getCsrf(client), "Idempotency-Key": crypto.randomUUID() };
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage(""); setFailed(false);
    try { await action(); }
    catch (error) { setFailed(true); setMessage(errorMessage(error instanceof Error ? error.message : undefined)); }
    finally { setPassword(""); setToken(""); setBusy(false); }
  }

  useEffect(() => {
    if (callbackStarted.current) return;
    callbackStarted.current = true;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code"), state = params.get("state");
    if (window.location.search) window.history.replaceState({}, "", window.location.pathname);
    if (code && state) {
      void (async () => {
        setBusy(true);
        try {
          const csrf = await getCsrf(client);
          const result = await client.POST("/api/v1/auth/google/callbacks", { body: { code, state }, params: { header: { "X-CSRFToken": csrf } } });
          if (!result.data || !result.response.ok) throw new Error("GOOGLE_UNAVAILABLE");
          setSession(validateSession(result.data));
        } catch { setFailed(true); setMessage(ar ? "تعذّر تأكيد Google. حاول تسجيل الدخول بالبريد." : "Google verification failed. Try email sign-in."); }
        finally { setBusy(false); }
      })();
    } else {
      void client.GET("/api/v1/session").then(result => {
        if (result.data && result.response.ok) setSession(validateSession(result.data));
      }).catch(() => setSession(null));
    }
  }, [ar]);

  useEffect(() => {
    if (!session || session.roles[0] !== "STUDENT") return;
    void client.GET("/api/v1/consents/disclosures").then(result => {
      if (result.response.ok && result.data && Array.isArray(result.data.items)) setDisclosures(result.data.items);
    }).catch(() => setDisclosures([]));
    void client.GET("/api/v1/account/deletions/impact").then(result => {
      if (result.response.ok && result.data) setImpact(result.data);
    }).catch(() => setImpact(null));
  }, [session]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const h = await headers();
      const params = { header: h };
      if (mode === "login") {
        const result = await client.POST("/api/v1/session/login", { body: { email, password }, params });
        if (!result.data || !result.response.ok) throw new Error(result.error?.code);
        setSession(validateSession(result.data));
        setMessage(ar ? "تم تسجيل الدخول." : "Signed in.");
        return;
      }
      const result = mode === "signup"
        ? await client.POST("/api/v1/auth/registrations", { body: { email, password, birth_date: birthDate, locale }, params })
        : mode === "verify"
          ? await client.POST("/api/v1/auth/email-verifications", { body: { challenge_token: token }, params })
          : mode === "resend"
            ? await client.POST("/api/v1/auth/email-verification-requests", { body: { email }, params })
          : mode === "resetRequest"
            ? await client.POST("/api/v1/auth/password-reset-requests", { body: { email }, params })
            : mode === "reset"
              ? await client.POST("/api/v1/auth/password-resets", { body: { challenge_token: token, password }, params })
              : mode === "recovery"
                ? await client.POST("/api/v1/account/recovery-requests", { body: { email }, params })
                : await client.POST("/api/v1/account/restorations", { body: { challenge_token: token }, params });
      if (!result.response.ok) throw new Error(result.error?.code);
      setMessage(["verify", "reset", "restore"].includes(mode)
        ? (ar ? "تم التحقق. يمكنك تسجيل الدخول الآن." : "Verified. You can now sign in.")
        : (ar ? "تم استلام الطلب. راجع رسالة التحقق إن كان الحساب مؤهلًا." : "Request received. Check your verification message if the account is eligible."));
    });
  }

  async function consent(disclosure: Disclosure, decision: "GRANT" | "REVOKE") {
    await run(async () => {
      const current = await client.GET("/api/v1/consents");
      const etag = current.response.headers.get("ETag");
      if (!current.response.ok || !etag) throw new Error();
      const result = await client.POST("/api/v1/consents", { body: { disclosure_id: disclosure.id, decision },
        params: { header: { ...await headers(), "If-Match": etag } } });
      if (!result.response.ok) throw new Error(result.error?.code);
      setMessage(ar ? "تم حفظ قرار الموافقة بإصدار جديد." : "Consent decision saved as a new version.");
    });
  }

  async function reauth() {
    const result = await client.POST("/api/v1/session/reauthentications", { body: { password }, params: { header: await headers() } });
    if (!result.data || !result.response.ok) throw new Error(result.error?.code);
    return result.data.reauthentication_token;
  }

  return <section aria-label={ar ? "إدارة الحساب" : "Account management"}>
    {!session ? <>
      <nav className="account-tabs" aria-label={ar ? "خيارات الحساب" : "Account options"}>
        {(Object.keys(labels) as Mode[]).map(item => <button key={item} type="button" disabled={busy}
          aria-pressed={mode === item} onClick={() => { setMode(item); setPassword(""); setToken(""); setMessage(""); }}>{labels[item]}</button>)}
      </nav>
      <form onSubmit={submit}>
        <h2>{labels[mode]}</h2>
        {["login", "signup", "resend", "resetRequest", "recovery"].includes(mode) && <label>{ar ? "البريد الإلكتروني" : "Email"}
          <input type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} /></label>}
        {["login", "signup", "reset"].includes(mode) && <label>{ar ? "كلمة المرور" : "Password"}
          <input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password}
            onChange={e => setPassword(e.target.value)} required minLength={mode === "login" ? 1 : 12} maxLength={256} /></label>}
        {mode === "signup" && <label>{ar ? "تاريخ الميلاد — 18 عامًا على الأقل" : "Date of birth — age 18 or older"}
          <input type="date" value={birthDate} onChange={e => setBirthDate(e.target.value)} required /></label>}
        {["verify", "reset", "restore"].includes(mode) && <label>{ar ? "رمز التحقق" : "Verification code"}
          <input type="text" autoComplete="one-time-code" value={token} onChange={e => setToken(e.target.value)} required maxLength={2048} /></label>}
        <button disabled={busy} type="submit">{busy ? (ar ? "جارٍ التحقق…" : "Verifying…") : labels[mode]}</button>
      </form>
    </> : <>
      <p>{ar ? "حساب مؤكد وبالغ. لا تُعرض بياناتك في الروابط أو السجلات." : "Verified adult account. Your details are kept out of URLs and logs."}</p>
      <button disabled={busy} onClick={() => void run(async () => {
        const result = await client.POST("/api/v1/session/logout", { params: { header: await headers() } });
        if (!result.response.ok) throw new Error();
        setSession(null); setDisclosures([]); setImpact(null); setEmail(""); setBirthDate("");
        setMessage(ar ? "تم الخروج." : "Signed out.");
      })}>{ar ? "تسجيل الخروج" : "Sign out"}</button>
      <h2>{ar ? "الموافقات" : "Consent"}</h2>
      <p>{ar ? "موافقة الذكاء الاصطناعي منفصلة واختيارية. لا تعني الموافقة أن معالجة بياناتك متاحة أو معتمدة." : "Personal AI consent is separate and optional. Consent does not enable or approve data processing."}</p>
      {disclosures.length === 0 && <p>{ar ? "لا توجد إفصاحات موافقة متاحة حاليًا." : "No consent disclosures are currently available."}</p>}
      {disclosures.map(disclosure => <article key={disclosure.id}>
        <h3><bdi>{disclosure.purpose}</bdi> · {disclosure.version}</h3><p>{disclosure.disclosure}</p>
        <button disabled={busy || !disclosure.available} onClick={() => void consent(disclosure, "GRANT")}>{ar ? "أوافق صراحة" : "I explicitly consent"}</button>{" "}
        <button disabled={busy} onClick={() => void consent(disclosure, "REVOKE")}>{ar ? "سحب الموافقة" : "Withdraw consent"}</button>
      </article>)}
      <h2>{ar ? "إعادة التحقق والحذف" : "Reauthentication and deletion"}</h2>
      <label>{ar ? "كلمة المرور الحالية" : "Current password"}<input type="password" autoComplete="current-password"
        value={password} onChange={e => setPassword(e.target.value)} /></label>
      <button disabled={busy || !password} onClick={() => void run(async () => {
        await reauth();
        const result = await client.POST("/api/v1/auth/google/authorizations", { body: { intent: "LINK" }, params: { header: await headers() } });
        if (!result.data || !result.response.ok) throw new Error(result.error?.code);
        window.location.assign(result.data.authorization_url);
      })}>{ar ? "ربط Google بعد إعادة التحقق" : "Link Google after reauthentication"}</button>
      <p>{ar ? "الحذف يوقف الوصول فورًا. تُثبت مهلة الاستعادة عند التأكيد، ولا تُقبل الاستعادة عند لحظة انتهائها. لا يعني الطلب محو النسخ الاحتياطية فورًا." : "Deletion stops access immediately. The recovery deadline is fixed at confirmation; restoration at that exact instant is too late. This does not promise immediate backup erasure."}</p>
      {impact && <p>{ar ? "المهلة الحالية بالأيام الكاملة: " : "Current period in full elapsed days: "}{impact.recovery_days} · <bdi>{impact.recovery_timezone}</bdi></p>}
      {!impact?.available && <p>{ar ? "الحذف غير متاح حاليًا حتى اعتماد سياسة الاحتفاظ." : "Deletion is currently unavailable pending retention policy approval."}</p>}
      <label className="confirm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
        {ar ? "أفهم أثر الحذف وأؤكد الطلب" : "I understand the impact and confirm deletion"}</label>
      <button disabled={busy || !confirmed || !password || !impact?.available} onClick={() => void run(async () => {
        const reauthentication_token = await reauth();
        const result = await client.POST("/api/v1/account/deletions", { body: { confirm_impact: true, reauthentication_token }, params: { header: await headers() } });
        if (!result.data || !result.response.ok) throw new Error(result.error?.code);
        setSession(null); setDisclosures([]); setImpact(null); setConfirmed(false); setEmail(""); setBirthDate("");
        setMessage((ar ? "توقف الوصول. آخر موعد للاستعادة UTC: " : "Access stopped. Recovery deadline UTC: ") + result.data.restore_until);
      })}>{ar ? "تأكيد حذف الحساب" : "Confirm account deletion"}</button>
    </>}
    <p role={failed ? "alert" : "status"} aria-live="polite">{message}</p>
  </section>;
}
