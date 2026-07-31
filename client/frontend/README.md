# Linda Protocol web client

Material UI React application for the Person 2 workflow screens:

- Sign in and role-aware actions
- Readiness tasks, blockers, and Action Matcher assist
- Three-role approval and signature verification
- Immutable packet, CAP, Husika, and offline-bundle exports
- Hash-chained audit log
- Policy/action-library viewer and partner API/webhook admin tools

```bash
cd client/frontend
npm install
npm run dev
```

The development server proxies `/api`, `/cap`, and `/integration` to
`http://localhost:8001`. It follows the operating system color scheme by
default; the AppBar lets the user persist an explicit light or dark override.
