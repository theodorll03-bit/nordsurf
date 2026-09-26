/* ---------- Konto (Supabase) ----------
   Innlogging med e-post-lenke (magic link), visningsnavn og sletting av
   konto. Bruker bare den offentlige publishable-nøkkelen - den er trygg å
   ha i frontend. Service-nøkkelen ligger ALDRI her, bare som GitHub-secret
   og som miljøvariabel i Edge Function-en som faktisk sletter kontoen
   (se supabase/functions/delete-account). */
(function(){
"use strict";

const SUPABASE_URL = "https://gtkjuauggcpufmqhthay.supabase.co";
const SUPABASE_KEY = "sb_publishable_jNPEaq6z-SNEuIGlBpD10A_nKycRGGa";

let client = null;
let state = { ready:false, user:null, profile:null };
const listeners = [];

function notify(){
  listeners.forEach(fn=>{ try{ fn(state); }catch(e){ console.error(e); } });
  window.dispatchEvent(new Event("authchange"));
}

async function loadProfile(userId){
  const { data, error } = await client.from("profiles").select("*").eq("id", userId).maybeSingle();
  if(error){ console.error("Fant ikke profil", error); return null; }
  return data;
}

async function applySession(session){
  state.user = session ? session.user : null;
  state.profile = session ? await loadProfile(session.user.id) : null;
}

async function init(){
  if(!window.supabase){ state.ready = true; notify(); return; } // ingen nett / CDN blokkert - appen funker uten konto
  client = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
  const { data:{ session } } = await client.auth.getSession();
  await applySession(session);
  state.ready = true;
  notify();
  client.auth.onAuthStateChange(async (_event, session)=>{
    await applySession(session);
    notify();
  });
}

function onChange(fn){ listeners.push(fn); }

async function sendLoginLink(email){
  if(!client) throw new Error("Ikke klar ennå");
  const redirectTo = location.href.split("#")[0].split("?")[0];
  const { error } = await client.auth.signInWithOtp({ email, options:{ emailRedirectTo: redirectTo } });
  if(error) throw error;
}

async function signOut(){
  if(!client) return;
  await client.auth.signOut();
}

async function saveDisplayName(name){
  if(!client || !state.user) throw new Error("Ikke innlogget");
  const { error } = await client.from("profiles").upsert({ id: state.user.id, display_name: name });
  if(error) throw error;
  state.profile = await loadProfile(state.user.id);
  notify();
}

async function deleteAccount(){
  if(!client || !state.user) return;
  const { data:{ session } } = await client.auth.getSession();
  const res = await fetch(SUPABASE_URL + "/functions/v1/delete-account", {
    method:"POST",
    headers:{ "Authorization":"Bearer " + session.access_token }
  });
  if(!res.ok) throw new Error("Sletting feilet (" + res.status + ")");
  await client.auth.signOut();
}

window.Auth = { init, onChange, sendLoginLink, signOut, saveDisplayName, deleteAccount, get state(){ return state; } };
init();
})();
