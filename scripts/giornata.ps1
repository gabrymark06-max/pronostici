# LA PIPELINE GIORNALIERA, A MANO.
#
# PERCHE' ESISTE. Normalmente questi job girano su GitHub Actions alle 03:00.
# Finche' l'account e' sospeso non gira niente, e ogni giorno fermo e' un
# giorno di pronostici che NON entra nel registro e non si recupera piu': i
# pronostici si scrivono prima della partita, o non si scrivono.
#
# Fa esattamente cio' che fa `daily.yml`, nello stesso ordine e con le stesse
# dipendenze fra un passo e l'altro. Le chiavi le legge da `.env`, dove ci sono
# gia'.
#
# COME SI USA: apri il terminale in VS Code e incolla
#
#     .\scripts\giornata.ps1
#
# Ci mette qualche minuto. Alla fine dice cosa ha scritto.
#
# QUANDO GITHUB TORNA, questo script non serve piu': i workflow ripartono da
# soli e rifanno la stessa cosa ogni notte.

# NON "Stop", e la ragione e' una trappola di PowerShell che vale la pena
# scrivere: i job stampano l'avanzamento su stderr — «PL 2025: 380 partite» non
# e' un errore, e' una riga di lavoro — e PowerShell avvolge OGNI riga di
# stderr di un programma esterno in un ErrorRecord. Con "Stop" la pipeline
# moriva al primo campionato letto, riuscito.
#
# A dire se un passo e' andato male ci pensa `$LASTEXITCODE`, che e' il codice
# di uscita vero del processo. E' l'unica cosa affidabile qui.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Le chiavi da .env. `python-dotenv` non e' fra le dipendenze: si legge a mano,
# che per tre righe e' piu' onesto di una libreria in piu'.
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$' -and $_ -notmatch '^\s*#') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
    }
}

# I quattro passi di `daily.yml`, nello stesso ordine. Ognuno dipende dal
# precedente: `settle` ha bisogno delle partite che `ingest` ha portato,
# `retrain` dei risultati che `settle` ha chiuso, `score` dei parametri che
# `retrain` ha ricalcolato.
$passi = @(
    @{ nome = "ingest";  cosa = "calendario e risultati" },
    @{ nome = "settle";  cosa = "esiti delle partite finite" },
    @{ nome = "retrain"; cosa = "riaddestramento dei modelli" },
    @{ nome = "score";   cosa = "pronostici di oggi" }
)

foreach ($p in $passi) {
    Write-Host ""
    Write-Host "--- $($p.nome): $($p.cosa)" -ForegroundColor Cyan
    python -m pronostici.jobs.$($p.nome)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FERMO su $($p.nome). I passi dopo dipendono da questo." -ForegroundColor Red
        exit 1
    }
}

# Le quote e il contorno: NON fermano la giornata se falliscono. Il pronostico
# e' gia' scritto e si regge sul modello; quote e formazioni lo arricchiscono.
Write-Host ""
Write-Host "--- quote di mercato" -ForegroundColor Cyan
python -m pronostici.jobs.quote --window-days 14

Write-Host ""
Write-Host "--- formazioni, arbitro e quote estese" -ForegroundColor Cyan
python -m pronostici.jobs.sofascore --window-days 4

Write-Host ""
Write-Host "--- stime sui giocatori" -ForegroundColor Cyan
python -m pronostici.jobs.giocatori --window-days 4

Write-Host ""
Write-Host "Fatto. I dati sono in data/." -ForegroundColor Green
Write-Host "Ricorda di committare:  git add data && git commit -m ""dati: giornata"""
