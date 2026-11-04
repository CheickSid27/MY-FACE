#!/bin/sh
# Sauvegarde de la base locale (service « db-sauvegarde », voir docker-compose.yml).
# Chaque nuit vers 3 h (heure d'Abidjan = UTC) : copie complete de la base
# dans /sauvegardes (dossier D:\MY FACE\sauvegardes du PC), 14 jours gardes.
# Le serveur MYFACE envoie ensuite la copie la plus recente dans Cloudflare R2
# (services/db_backup.py) : si le disque du PC lache, rien n'est perdu.
set -u
DOSSIER=/sauvegardes
GARDER_JOURS=14

sauvegarder() {
    nom="myface-$(date -u +%Y%m%d-%H%M).dump"
    if pg_dump --no-owner --no-acl -Fc -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$DOSSIER/$nom.tmp"; then
        mv "$DOSSIER/$nom.tmp" "$DOSSIER/$nom"
        echo "$(date -u '+%F %T') sauvegarde faite : $nom ($(du -h "$DOSSIER/$nom" | cut -f1))"
    else
        rm -f "$DOSSIER/$nom.tmp"
        echo "$(date -u '+%F %T') ECHEC de la sauvegarde"
    fi
    find "$DOSSIER" -name 'myface-*.dump' -mtime +"$GARDER_JOURS" -delete
}

# Au demarrage : une sauvegarde tout de suite s'il n'y en a pas de moins de 24 h
if [ -z "$(find "$DOSSIER" -name 'myface-*.dump' -mtime -1 2>/dev/null)" ]; then
    sauvegarder
fi
while true; do
    # attendre le prochain 3 h du matin (UTC = heure d'Abidjan)
    maintenant=$(date -u +%s)
    demain_3h=$(( (maintenant / 86400 + 1) * 86400 + 3 * 3600 ))
    [ $(( demain_3h - maintenant )) -gt 86400 ] && demain_3h=$(( demain_3h - 86400 ))
    sleep $(( demain_3h - maintenant ))
    sauvegarder
done
