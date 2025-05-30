# DyNASty

**DyNASty** est un projet de démonstration d’un VPN MPLS L3 multi-client sur un backbone provider dynamique. Ce README présente les objectifs, l’architecture, les prérequis et les étapes de déploiement et de validation, sans entrer dans les détails de plan d’adressage ou de numérotation d’AS.

## Objectifs

* Illustrer la mise en place d’un VPN MPLS L3 multi-tenant en partitionnant plusieurs VRF.
* Montrer l’usage de protocoles de transport (OSPF + LDP/MPLS) et de signalisation VPN (MP-BGP).
* Utiliser un route-reflector pour simplifier la topologie iBGP.
* Valider la connectivité de bout en bout entre clients de VRF distinctes.

## Architecture

* **Routeurs Provider (P)**

  * Assurent le transport MPLS et le routage interne (OSPF).
  * Établissent des sessions LDP pour l’échange de labels.
  * Un routeur joue le rôle de Route‑Reflector pour les sessions VPNv4.

* **Routeurs Provider-Edge (PE)**

  * Attachés aux routeurs P pour le back‑end MPLS et aux clients CE pour l’accès.
  * Définissent plusieurs VRF pour isoler les espaces de routage.
  * Utilisent MP‑BGP pour échanger les préfixes entre PE.

* **Clients Edge (CE)**

  * Simulent différents clients/tenants sur chaque VRF.
  * Peuplent leur LAN avec des préfixes distincts.
  * Dépendent de la VRF pour le routage et la diffusion de routes.

## Prérequis

* Plateforme réseau compatible MPLS, OSPF, BGP, VRF et LDP.
* Accès aux équipements (physiques ou virtualisés) pour déployer les configurations.
* Outils de capture/troubleshooting (ex : Wireshark, outils en ligne de commande).

## Étapes de déploiement

1. **Configuration des VRF sur les PE**

   * Créer chaque VRF avec ses route‑targets d’import/export.
2. **OSPF et LDP sur le backbone**

   * Activer OSPF sur les liens P–P et P–PE.
   * Activer LDP/MPLS pour l’échange de labels.
3. **MP‑BGP VPNv4**

   * Établir les sessions iBGP full‑mesh/route‑reflector.
   * Activer l’address-family VPNv4 et propager les route‑targets.
4. **Configuration des CE**

   * Définir l’accès WAN vers le PE.
   * Annoncer les préfixes clients dans la VRF appropriée.

## Vérification

* **Transport MPLS**

  * `show mpls ldp neighbor` et `show mpls forwarding-table` pour valider l’échange de labels.
* **OSPF**

  * `show ip ospf neighbor` pour vérifier l’adjacence backbone.
* **MP‑BGP VPNv4**

  * `show bgp vpnv4 unicast summary` pour s’assurer de la propagation des préfixes.
* **Connectivité CE→CE**

  * Pings entre clients de VRF différentes pour tester l’isolation et le routage.

## Bonnes pratiques

* Séparer les route-targets pour chaque VRF pour préserver l’isolation.

* Utiliser un route‑reflector pour réduire le full‑mesh iBGP.

* Ajuster les timers OSPF, LDP et BGP en fonction des besoins de convergence.

* Automatiser les validations de bout en bout (scripts de ping, checks BGP/MPLS).

Ce README fournit un cadre générique pour reproduire le projet DyNASty sans les détails spécifiques de numérotation d’AS ou d’adressage IP. Vous pouvez adapter les variables (ASNs, sous‑réseaux) selon votre environnement.
