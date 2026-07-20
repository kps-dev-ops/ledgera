module.exports = {
    // Tailwind purge toute classe qu'il ne trouve pas ici. Une classe déclarée dans une
    // source non listée disparaît silencieusement du CSS : le contrôle s'affiche sans
    // style, sans la moindre erreur. Toute source qui écrit une classe doit donc figurer
    // dans cette liste — y compris le code Python (apps/core/templatetags/formulaires.py
    // choisit la classe daisyUI selon la famille de widget).
    // L'étape Node du Dockerfile copie exactement `theme`, `templates` et `apps`.
    content: [
        '../templates/**/*.html',
        '../../templates/**/*.html',
        '../../**/templates/**/*.html',
        '../../apps/**/*.py',
    ],
    theme: {
        extend: {
            colors: {
                ledgera: {
                    50:  '#f0f7f4',
                    100: '#dceae2',
                    500: '#2d6a4f',
                    600: '#1b4332',
                    700: '#081c15',
                },
                debit:          '#dc2626',
                credit:         '#16a34a',
                'balance-ok':   '#16a34a',
                'balance-ko':   '#dc2626',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('daisyui'),
    ],
    daisyui: {
        themes: [{
            ledgera: {
                primary:    '#2d6a4f',
                secondary:  '#1b4332',
                accent:     '#d97706',
                neutral:    '#1f2937',
                'base-100': '#ffffff',
                info:       '#0ea5e9',
                success:    '#16a34a',
                warning:    '#f59e0b',
                error:      '#dc2626',
            },
        }],
    },
};
