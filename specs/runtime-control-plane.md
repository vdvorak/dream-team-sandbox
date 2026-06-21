---
feature-id: runtime-control-plane
flags: has_ui: false · touches_db: false · has_server: true
acceptance: acceptance/runtime-control-plane.md
note: slice 1 — lifecycle core; repozitář / soubory / terminál deferred na navazující wave (AC-6/7/8)
---
# Runtime control-plane — lifecycle core

## Cíl

Služba řídí životní cyklus izolovaných pracovních prostředí. Každé prostředí odpovídá
jednomu zdrojovému repozitáři. Klient může prostředí zajistit, číst jeho stav, uspat a
zrušit — bez znalosti toho, na čem prostředí fyzicky běží.

## Aktér a cíl

**Klient (aplikace nebo standalone volač)** chce pro daný projekt zajistit prostředí,
sledovat jeho stav, dočasně ho uspat a trvale zrušit. Chce přitom dostat přístupový
handle, aniž by znal podkladový substrát.

**Operátor** chce službu spustit bez závislosti na cloudové infrastruktuře a ověřit
celý lifecycle lokálně.

## Hlavní scénář

Klient se autentizuje → zajistí prostředí pro projekt ze zdrojového repozitáře →
prostředí se připravuje; jakmile je bezpečnostní enforcement aktivní, přejde do stavu
připraveno → klient dostane přístupový handle → klient čte stav prostředí → klient
prostředí uspí → klient prostředí zruší.

Zdravotní kontrola služby je přístupná bez autentizace a sdělí, zda je služba v pořádku,
omezeně funkční nebo nedostupná.

## Chování a garance

**Fail-closed:** Prostředí se stane „připravené" výhradně tehdy, když je bezpečnostní
enforcement prokazatelně aktivní. Nelze-li enforcement zajistit, prostředí v stavu
„připravené" neskončí — vrátí se chyba.

**Enforcement nelze oslabit ani přečíst:** Žádná operace neumožňuje přes tuto službu
enforcement zmírnit, obejít ani zobrazit jeho konfiguraci.

**Idempotence:** Opakované zajištění téhož prostředí nevytvoří duplikát. Uspání ani
zrušení již uspaného / zrušeného prostředí neprodukuje chybu.

**Souběžnost:** Souběžné zajištění stejného projektu vede vždy k jedinému prostředí.

**Vazba repozitář–prostředí:** Jedno prostředí je trvale svázáno s jedním repozitářem.
Pokus o zajištění s jiným repozitářem na živém prostředí je odmítnut.

**Nevratnost zrušení:** Zrušené prostředí nelze obnovit. Opětovné zajištění po zrušení
spustí čisté nové prostředí.

**Přežití stavu:** Stav prostředí přetrvává mezi voláními.

**Standalone:** Služba je použitelná bez aplikační identity — čistě přes service volání.

**Neprůhledné handly:** Přístupový handle je pro klienta neprůhledný; z jeho obsahu
nelze odvodit, na čem prostředí běží.

**Zaměnitelný enforcement provider:** Bezpečnostní enforcement je delegován na
vyměnitelný provider. Provider buď potvrdí, že enforcement je aktivní a předá handle,
nebo vrátí chybu — třetí možnost neexistuje. Lokální/vývojová varianta reálný
enforcement nevynucuje; slouží výhradně pro provoz nasucho.

## Scope

**In:**
- Čtyři lifecycle operace: zajisti / stav / uspi / zruš prostředí.
- Zdravotní kontrola služby.
- Standalone provoz bez aplikační identity.
- Fail-closed garance: prostředí nikdy „připravené" bez aktivního enforcementu.

**Out (deferred):**
- Čtení stavu repozitáře.
- Čtení souborů v prostředí.
- Připojení terminálu.
- Reálné klonování repozitáře a spuštění agenta (navazující wave).
- Trvanlivá persistence stavu.

## Edge cases

- **Uspání při probíhající přípravě:** Pokud klient uspí prostředí, které se ještě
  připravuje, vrátí se úspěšná odpověď s aktuálním stavem. Příprava není přerušena.
- **Zdravotní stav:** Kontrola rozliší tři výsledky — v pořádku / omezeně / nedostupné.
  Omezeně nastane, když provider odpovídá, ale hlásí degradaci. Nedostupné nastane,
  když provider vůbec neodpoví.
- **Zajištění po zrušení:** Zajistit zrušené prostředí je platná operace — spustí nový
  provisioning cyklus pro čisté prostředí.
