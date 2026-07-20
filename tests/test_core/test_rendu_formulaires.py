"""Rendu des formulaires : les champs doivent porter les classes daisyUI du projet.

Contexte du bug corrige ici : les formulaires passaient par crispy-tailwind, dont les
gabarits vivent dans site-packages. Or Tailwind ne scanne que `templates/` et `apps/`
(cf. theme/static_src/tailwind.config.js, et l'etape Node du Dockerfile qui ne copie
que ces dossiers). Toutes les classes ecrites par crispy-tailwind etaient donc purgees
du CSS compile : les champs s'affichaient sans style, et le chevron des <select>
-- un <svg class="fill-current h-4 w-4"> dans un <div class="pointer-events-none
absolute ..."> -- perdait taille et positionnement, d'ou un chevron noir geant affiche
dans le flux, sous le champ.

La correction consiste a rendre les champs depuis des gabarits du projet, donc scannes.
"""

from pathlib import Path

from django import forms
from django.conf import settings
from django.template.loader import render_to_string

RACINE = Path(__file__).resolve().parents[2]


class FormulaireDemo(forms.Form):
    """Couvre une famille de widget par branche du gabarit."""

    intitule = forms.CharField(label="Intitule")
    montant = forms.DecimalField(max_digits=10, decimal_places=2)
    categorie = forms.ChoiceField(choices=[("a", "A"), ("b", "B")])
    commentaire = forms.CharField(widget=forms.Textarea, required=False, help_text="Facultatif")
    actif = forms.BooleanField(required=False)
    piece = forms.FileField(required=False)
    jeton = forms.CharField(widget=forms.HiddenInput, required=False)


def rendu(form=None, **contexte):
    return render_to_string("ui/formulaire.html", {"form": form or FormulaireDemo(), **contexte})


class TestClassesDaisyUI:
    def test_les_champs_portent_la_classe_daisyui_de_leur_famille(self):
        html = rendu()
        assert 'class="input input-bordered w-full"' in html          # CharField
        assert "select select-bordered w-full" in html                # ChoiceField
        assert "textarea textarea-bordered w-full" in html            # Textarea
        assert "checkbox checkbox-primary" in html                    # BooleanField
        assert "file-input file-input-bordered w-full" in html        # FileField

    def test_aucun_reste_du_chevron_crispy(self):
        """Le marqueur exact du bug : il ne doit plus jamais reapparaitre."""
        html = rendu()
        assert "pointer-events-none" not in html
        assert "h-4 w-4" not in html
        assert "<svg" not in html

    def test_les_champs_caches_sont_rendus_sans_habillage(self):
        html = rendu()
        assert 'type="hidden"' in html
        assert 'name="jeton"' in html
        # Un champ cache ne doit pas trainer un libelle visible.
        assert "Jeton" not in html

    def test_libelle_aide_et_asterisque_de_champ_requis(self):
        html = rendu()
        assert "Intitule" in html
        assert "Facultatif" in html
        assert "text-error" in html  # asterisque des champs requis


class TestMiseEnLigne:
    """Les ecrans fiscaux posent leurs champs cote a cote dans un conteneur flex.
    En mode empile, `w-full` sur chaque champ ferait retomber chacun sur sa ligne."""

    def test_le_mode_en_ligne_retire_les_largeurs_pleines(self):
        html = rendu(en_ligne=True)
        assert "w-full" not in html
        assert "select select-bordered" in html
        assert "mb-0" in html

    def test_le_mode_empile_reste_le_defaut(self):
        assert "w-full" in rendu()

    def test_une_case_a_cocher_ne_s_etire_jamais(self):
        """Une case est une pastille de taille fixe : `w-full` la deformerait."""
        html = rendu()
        assert 'class="checkbox checkbox-primary"' in html


class TestErreurs:
    def test_les_erreurs_de_champ_sont_affichees_et_marquent_le_widget(self):
        form = FormulaireDemo(data={"montant": "abc", "categorie": "a"})
        assert not form.is_valid()
        html = rendu(form)
        assert "input-error" in html
        assert "Ce champ est obligatoire" in html or "This field is required" in html

    def test_les_erreurs_globales_sont_affichees(self):
        class FormulaireRefusant(forms.Form):
            nom = forms.CharField(required=False)

            def clean(self):
                raise forms.ValidationError("Periode deja declaree.")

        form = FormulaireRefusant(data={})
        assert not form.is_valid()
        html = rendu(form)
        assert "Periode deja declaree." in html
        assert "alert-error" in html


class TestGardeAntiRegression:
    """Empeche de re-deleguer le rendu des formulaires a un paquet non scanne par Tailwind.

    C'est la garde qui compte vraiment : le bug n'etait pas une faute de frappe, mais un
    rendu delegue a des gabarits que la chaine de build ne voit pas. Tant que le rendu
    reste dans templates/ et apps/, les classes survivent au purge -- y compris dans
    l'image Docker, dont l'etape Node ne copie que ces dossiers.
    """

    def test_aucun_gabarit_n_utilise_crispy(self):
        # On cible l'USAGE (`|crispy`, `{% crispy %}`, chargement de la bibliotheque),
        # pas la simple mention : les commentaires qui expliquent pourquoi crispy a ete
        # retire doivent rester, ce sont eux qui evitent la reintroduction.
        usages = ("|crispy", "{% crispy", "crispy_forms_tags", "tailwind_field", "tailwind_filters")
        fautifs = [
            str(f.relative_to(RACINE))
            for f in (RACINE / "templates").rglob("*.html")
            if any(u in f.read_text(encoding="utf-8") for u in usages)
        ]
        assert fautifs == [], f"Rendu delegue hors du perimetre scanne par Tailwind : {fautifs}"

    def test_crispy_n_est_plus_une_application_installee(self):
        assert not [a for a in settings.INSTALLED_APPS if "crispy" in a]

    def test_tous_les_gabarits_compilent(self):
        """Une erreur de syntaxe de gabarit ne se voit qu'a la requete : la suite peut
        rester verte alors qu'une page est cassee en production. On les compile toutes."""
        from django.template.loader import get_template

        casses = {}
        for f in (RACINE / "templates").rglob("*.html"):
            nom = f.relative_to(RACINE / "templates").as_posix()
            try:
                get_template(nom)
            except Exception as e:  # noqa: BLE001 - on veut le rapport complet, pas le 1er echec
                casses[nom] = f"{type(e).__name__}: {e}"
        assert casses == {}, f"Gabarits qui ne compilent pas : {casses}"

    def test_toute_source_declarant_des_classes_est_scannee_par_tailwind(self):
        """Le piege central de ce projet, sous sa forme generale.

        Tailwind purge toute classe absente des sources qu'il scanne, SANS erreur : le
        controle s'affiche simplement sans style. C'est ce qui est arrive deux fois --
        avec les gabarits de crispy-tailwind (dans site-packages), puis avec le
        templatetag qui choisit la classe daisyUI en Python alors que les globs ne
        listaient que des *.html.

        On verifie donc l'invariant lui-meme : tout fichier de apps/ ou templates/ qui
        ecrit une classe daisyUI doit etre couvert par `content` de tailwind.config.js.
        """
        import re

        config = (RACINE / "theme" / "static_src" / "tailwind.config.js").read_text(encoding="utf-8")
        motifs = re.findall(r"'([^']+)'", config.split("content:")[1].split("]")[0])

        scannes: set[Path] = set()
        for motif in motifs:
            base, reste = RACINE / "theme" / "static_src", motif
            while reste.startswith("../"):
                base, reste = base.parent, reste[3:]
            scannes |= {p.resolve() for p in base.glob(reste)}

        # Classes daisyUI distinctives : leur presence signale un fichier qui habille l'UI.
        MARQUEURS = ("input-bordered", "select-bordered", "btn-primary", "card-body", "label-text")
        oublies = []
        for dossier in ("apps", "templates"):
            for f in (RACINE / dossier).rglob("*"):
                if f.suffix not in (".py", ".html") or "__pycache__" in f.parts:
                    continue
                if any(m in f.read_text(encoding="utf-8") for m in MARQUEURS) and f.resolve() not in scannes:
                    oublies.append(str(f.relative_to(RACINE)))
        assert oublies == [], (
            "Ces fichiers declarent des classes daisyUI mais ne sont pas scannes par "
            f"Tailwind — leurs classes seront purgees du CSS : {oublies}"
        )
