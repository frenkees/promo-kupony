# Dokumentace — Systém promo kuponů
**Pro běžného uživatele. Bez technického žargonu.**

---

## Co to je
Aplikace na správu papírových promo kartiček v síti restaurací. Každá kartička má svůj **QR kód** a **4místné číslo**. Když ji dáte zákazníkovi, „vydáte" ji v aplikaci. Když ji zákazník přinese zpět pro odměnu, „uplatníte" ji a kartičku si vezmete zpátky — může se použít znovu.

**Proč to má smysl:** papírovou kartičku jde okopírovat, ale v aplikaci má každé číslo jen jeden „život" — uplatnit se dá vždy jen jednou. Kopie je tím pádem k ničemu. Navíc majitel vidí přes všechny pobočky, co se s kartičkami děje.

---

## Tři druhy přihlášení
Podle toho, jakým účtem se přihlásíte, uvidíte jinou část aplikace:

1. **Účet restaurace** — na služebním telefonu na pobočce. Po přihlášení se rovnou objeví skenovací obrazovka. Slouží jen k vydávání a uplatňování kartiček.
2. **Manažerský účet** — administrace pro majitele/manažera. Přehledy, historie kartiček, vyřazování zničených kartiček, nahrávání nových.
3. **Master účet** — nejvyšší, pro správce systému (vývojáře). Zakládá restaurace a vytváří jim přihlašovací účty a hesla.

---

## Pro obsluhu na telefonu (účet restaurace)

Přihlásíte se **jednou** a telefon je připravený. Žádné přepínání uživatelů, žádné složitosti.

### Vydání kartičky zákazníkovi
1. Vezmete volnou kartičku.
2. Naskenujete její QR (tlačítko **Skenovat**, podle potřeby zapnete blesk) **nebo** napíšete 4místné číslo.
3. Obrazovka ukáže **modře „VOLNÁ"** a tlačítko **VYDAT**.
4. Ťuknete na **VYDAT** → zezelená „VYDÁNO ✓". Kartičku předáte zákazníkovi. Hotovo.

### Uplatnění (zákazník přinesl kartičku pro odměnu)
1. Naskenujete QR nebo napíšete číslo.
2. Obrazovka ukáže **oranžově „K UPLATNĚNÍ"** a tlačítko **UPLATNIT**.
3. Ťuknete na **UPLATNIT** → zezelená „UPLATNĚNO ✓". Vydáte odměnu a **kartičku si vezmete zpět** (vrátí se do oběhu).

### Barvy napovídají vše
- **Zelená** = v pořádku, akce proběhla.
- **Oranžová** = kartička čeká na uplatnění, můžete vydat odměnu.
- **Červená** = něco nesedí (neplatná, zničená, nebo nebyla vydaná).

### Když to řekne „Nevydáno přes systém" (červená)
Někdy se stane, že kartičku vydala jiná pobočka, ale zapomněla to zadat do systému. Aby vás to nezdrželo:
1. Objeví se tlačítko **„Uplatnit přesto"**.
2. Ťuknete na něj → vyberete **důvod** ze seznamu (povinné).
3. Akce proběhne, ale **uloží se jako podezřelá** — majitel ji uvidí ve svém přehledu a může se na ni podívat.

Používejte „Uplatnit přesto" jen výjimečně. Je to nouzové tlačítko, ne běžný postup.

> Pokud aplikace hlásí, že jste **offline**, počkejte na připojení — kartičky se musí ověřit online, aby nešlo totéž číslo uplatnit dvakrát na dvou místech zároveň.

---

## Pro manažera (manažerský účet)

Po přihlášení vidíte administraci s těmito částmi:

### Přehled
- **Otevřený závazek** — kolik vydaných kartiček je „venku" a čeká na uplatnění. To je počet odměn, které ještě dlužíte. Důležité číslo.
- **Míra uplatnění** — kolik z vydaných kartiček se vrátilo.
- **Stav fondu** — kolik kartiček je volných, vydaných a vyřazených.
- **Podle poboček** — kolik která pobočka vydala a uplatnila.

### Podezřelé akce
Tabulka jen s akcemi, které systém označil jako podezřelé — například uplatnění „přesto", akce mimo provozní dobu nebo z jiného než obvyklého zařízení. U každé vidíte čas, kód kartičky, kdo a kde. Slouží k tomu, abyste si je mohli osobně prověřit.

### Historie kartičky
Zadáte číslo kartičky a uvidíte **celou její historii** — kdy a kde byla vydána, kdy uplatněna, kdo to udělal. Užitečné při řešení sporů.

### Vyřazení zničené kartičky
Když se kartička poškodí nebo ztratí, najdete ji a dáte **Vyřadit** (s důvodem). Tím přestane platit (nejde vydat ani uplatnit), ale její historie v systému zůstane. Vyřazená kartička se už nevrací zpátky.

### Nahrání nových kartiček
Když potřebujete doplnit fond, nahrajete **CSV soubor** s čísly (jak ho vyrobit, viz níže). Systém čísla založí jako volná.

---

## Pro správce systému (master účet)
- **Restaurace** — přidáte/upravíte pobočky.
- **Účty** — vytvoříte přihlašovací účet pro restauraci nebo manažera, nastavíte mu počáteční heslo a můžete heslo kdykoli resetovat nebo účet vypnout.

Při úplně prvním spuštění systému se master účet vytvoří automaticky z nastavení (viz instalace). Po prvním přihlášení vás aplikace **donutí změnit heslo** — udělejte to hned.

---

## Výroba kartiček (čísla + QR)
V projektu je skript `generate_cards.py`, který vyrobí seznam náhodných 4místných čísel a (volitelně) k nim QR obrázky.

1. Potřebujete nainstalovaný Python. Pro QR jednou spusťte:
   ```
   pip install "qrcode[pil]"
   ```
2. Vygenerování 1000 kartiček i s QR obrázky:
   ```
   python generate_cards.py -n 1000 --qr
   ```
   Vznikne soubor `karticky.csv` (čísla a názvy QR souborů) a složka `qr/` s obrázky.
3. **Tisk:** CSV i QR obrázky vložíte do šablony v InDesignu (hromadné slučování dat) nebo si necháte vyrobit PDF. Na kartičku patří: typ odměny (jídlo / nápoj / menu), 4místné číslo a QR.
4. **Vložení do systému:** stejný soubor `karticky.csv` nahrajete v manažerské administraci přes **Nahrání nových kartiček**.

> Vygenerovaná čísla jsou náhodná, takže se nedají snadno tipovat. Vyřazené číslo už znovu nepoužívejte.

---

## Instalace a nasazení (krok za krokem)
Tohle dělá technik při prvním rozjetí. Když to jednou běží, dál se o to skoro nestaráte.

**Co potřebujete:** malý server na internetu (VPS) a vlastní doménu (např. `kupony.vasefirma.cz`).

1. **Doména na server.** U svého poskytovatele domény nastavte „A záznam" tak, aby doména ukazovala na IP adresu serveru.
2. **Na serveru nainstalujte Docker** (a Docker Compose). To je program, který aplikaci spustí v „krabičkách", aby vše fungovalo samo.
3. **Nahrajte projekt** na server.
4. **Nastavte hesla.** Zkopírujte soubor `.env.example` na `.env`:
   ```
   cp .env.example .env
   ```
   a v souboru `.env` vyplňte: hesla k databázi, tajný klíč `JWT_SECRET` (dlouhý náhodný text), přihlašovací jméno a heslo master účtu (`MASTER_LOGIN`, `MASTER_PASSWORD`) a vaši doménu (`DOMAIN`).
5. **Spusťte vše jedním příkazem:**
   ```
   docker compose up -d --build
   ```
   Systém si sám připraví databázi, vytvoří master účet a získá HTTPS certifikát (zabezpečené připojení — je nutné, jinak nefunguje kamera).
6. **Otevřete doménu v prohlížeči**, přihlaste se jako **master**, změňte heslo.
7. **Vytvořte pobočky a účty** (master → Restaurace, Účty).
8. **Vyrobte a nahrajte kartičky** (viz výše).
9. Hotovo — restaurace se přihlásí svým účtem na telefonu a může začít.

---

## Zálohy
Data jsou srdce systému (kdo komu dluží odměnu + historie). Proto se denně automaticky zálohují.

- V projektu je skript `backup.sh`, který každou noc uloží kopii databáze a (doporučeno) ji zašifrovanou pošle i mimo server — kdyby se serveru něco stalo.
- Nastavení (udělá technik jednou): přidá se „cron" úloha, např. každý den ve 3 ráno.
- **Jednou za čas vyzkoušejte obnovu** ze zálohy, ať máte jistotu, že funguje.

---

## Časté problémy
- **Nejde kamera / skenování.** Aplikace musí běžet na adrese se zámečkem (HTTPS) a v běžném prohlížeči (Safari/Chrome), ne uvnitř prohlížeče ve Facebooku apod. Povolte přístup ke kameře, když se zeptá.
- **Zapomenuté heslo restaurace nebo manažera.** Přihlásí se master a v sekci Účty heslo resetuje.
- **Aplikace hlásí offline.** Není připojení k internetu. Kartičky se musí ověřovat online, počkejte na signál.
- **Telefon hlásí akci jako „podezřelou".** Nic se neblokuje, jen se to zapíše pro manažera. Když jde o legitimní situaci (jiný telefon, večerní akce), nic neřešíte — manažer to uvidí a posoudí.
- **Kartička se zničila.** Manažer ji v administraci vyřadí, fond doplníte novými čísly.
