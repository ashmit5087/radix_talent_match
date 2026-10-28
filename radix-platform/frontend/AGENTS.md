<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Rules
- API contracts live in src/lib/radix/contracts.ts, clients in services.ts, demo fixtures in mock.ts: this keeps backend wiring in one place.
- Workspace pages are nested under the /app layout route (src/routes/app.tsx), so they share one shell.
- Landing theme overrides are scoped to `.landing` in the global stylesheet, keeping shared controls themed without changing workspace pages.
