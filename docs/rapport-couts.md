# Mon suivi des coûts

J’ai créé le groupe `rg-projet-ft` en Suisse Nord avec les étiquettes `projet=dscc` et `equipe=ft`. Mon budget de groupe est de 22,85 €, soit environ 25 $ au taux de référence retenu le 23 novembre. Azure doit m’envoyer un courriel à 20 %, 50 % et 80 %.

| Étape | Montant | Ce que j’ai vérifié |
|---|---:|---|
| Estimation initiale pour 15 jours | 0 à 3 $ | Services de faible volume, Container Apps à zéro réplica au repos, Cosmos DB Free Tier |
| Lecture Azure du 24 novembre | 0,00 € | Valeur `currentSpend` affichée par le budget, susceptible d’arriver avec retard |
| Coût final à J15 | À relever le 8 décembre | Cost Analysis filtré sur `projet=dscc` |
| Écart final | À calculer | Différence entre coût final et estimation |

Après ma soutenance du 2 décembre, je supprimerai le groupe du projet et conserverai une capture de `az group exists -n rg-projet-ft` indiquant `false`. Je vérifierai aussi les éventuels groupes `DefaultResourceGroup-*` liés à ce projet. Le coût historique restera à relever pour le rapport final.
