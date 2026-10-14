# Component scope

Use this flow when the request concerns one element, a single component file, or an explicitly bounded component. If it is unclear whether the user wants a component or a page, ask once; default to the smaller artifact when there is no answer.

Run the page preflight, inherit the project's tokens and genre, and skip page-only macrostructure, hero, navigation, footer, and project-memory rotation.

For an interactive component, implement and demonstrate default, hover, focus-visible, active, disabled, loading, error, and success states. Provide a small preview wrapper only when it helps review the state matrix; do not require a throwaway file for a simple component change. Use named tokens and visible focus, test the applicable accessibility and interaction gates, and stamp the artifact as component-scoped so later Hallmark runs do not treat it as a page.
