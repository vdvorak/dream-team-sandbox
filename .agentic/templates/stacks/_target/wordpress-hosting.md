---
cache_key: template-stack-target-wordpress-hosting-v1.0
type: template
---

# Deploy target — WordPress shared / managed hosting

Deploy pattern pro WordPress projekty na klasickém hostingu (Wedos, cPanel,
Plesk, WP Engine apod.). Žádný Docker, žádné kontejnery — PHP běží přímo
na hostingu. Alfred vlastní deploy kód (rsync / FTP / WP CLI); tento fragment
definuje posvěcený pattern.

---

```markdown
## Deploy — WordPress hosting (shared / managed)

| Building block | Volba |
|---|---|
| Platforma | Shared nebo managed WordPress hosting |
| Kontejnerizace | **Žádná** — PHP / WordPress běží nativně na hostingu |
| Databáze | MySQL / MariaDB poskytovaná hostingem |
| Deploy mechanismus | rsync přes SSH nebo SFTP; případně WP CLI (`wp plugin install`) |
| Migrace DB | WP CLI (`wp db import`) nebo phpMyAdmin; schema migrace v custom pluginu při aktivaci |
| Secrets | Hosting admin panel / `.env` mimo VCS nebo `wp-config.php` (generován při deployi) |
| Statika | WordPress servíruje nativně; Nginx/Apache konfigurace v hostingu |

**Kdy použít:** WordPress projekt na klasickém hostingu — pneukarnik vzor.
Provozní jednoduchost: hosting za ops, nulová Docker zátěž.

**Kdy NE:** potřeba vlastní server-side logiky mimo WP ekosystém, nebo Docker
je vyžadován compliance / CI prostředím → přejít na `_target/docker-compose`.

**Co Alfred ladí:** rsync cesta, SSH credentials (z CI secrets), WP CLI příkazy
pro migrace a flush cache. Žádný Dockerfile ani compose soubor se negeneruje.
```
