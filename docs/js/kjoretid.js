/* Nordsurf: kjøretid fra startstedet til spoten, i minutter (design B 4.0, SPEC §6A: «REGION · KJØRETID · ORD»).
   En enkel tabell uten rutetjeneste (PROMPT T3 steg 3). Tallene er Theodors anslag fra skissene 12.11.2026 og er
   IKKE bekreftet. En spot uten tall viser ingen kjøretid - aldri et anslag regnet fra luftlinje.
   Bare offentlige spots (id fra spots.json) skal stå her. `fra` brukes også til lyset i topplinja på Hjem. */
window.KJORETID = {
  fra: {navn: "Tromsø", lat: 69.6492, lon: 18.9553},
  min: {grotfjord: 45, tromvik: 50, lenangsoyra: 80, ersfjordstranda: 180, unstad: 420},
};
