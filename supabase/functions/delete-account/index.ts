// Nordsurf: sletter en brukers konto fullstendig (auth.users + profiles).
// Krever service-rollen, som klienten aldri får se - derfor kjører dette
// server-side som en Edge Function, ikke i frontend.
//
// SUPABASE_URL og SUPABASE_SERVICE_ROLE_KEY settes automatisk av Supabase
// for alle Edge Functions og trenger ikke legges inn manuelt.
//
// Deploy: lim inn i Supabase-dashbordet under Edge Functions -> New function
// (kalt "delete-account"), eller med Supabase CLI: supabase functions deploy delete-account

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const authHeader = req.headers.get("Authorization") || "";
  const token = authHeader.replace("Bearer ", "");
  if (!token) {
    return new Response("Mangler token", { status: 401 });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(supabaseUrl, serviceKey);

  // Verifiser hvem brukeren faktisk er ut fra deres egen innloggingstoken,
  // slik at en bruker aldri kan be om at NOEN ANNEN konto slettes.
  const { data: userData, error: userErr } = await admin.auth.getUser(token);
  if (userErr || !userData?.user) {
    return new Response("Ugyldig token", { status: 401 });
  }
  const userId = userData.user.id;

  // profiles-raden slettes automatisk via "on delete cascade", men vi
  // sletter den eksplisitt her også i tilfelle den mangler.
  await admin.from("profiles").delete().eq("id", userId);

  const { error: delErr } = await admin.auth.admin.deleteUser(userId);
  if (delErr) {
    return new Response("Sletting feilet: " + delErr.message, { status: 500 });
  }

  return new Response("ok", { status: 200 });
});
