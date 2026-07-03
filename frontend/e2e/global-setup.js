import { execSync } from "child_process";
import path from "path";

export default async function globalSetup() {
  if (process.env.PLAYWRIGHT_SKIP_SEED) return;

  const backendDir = path.join(process.cwd(), "../backend");
  execSync(".venv/bin/python manage.py seed_demo", {
    cwd: backendDir,
    stdio: "inherit",
  });
  execSync(".venv/bin/python manage.py beta_scene_loop --skip-notify --seed-only", {
    cwd: backendDir,
    stdio: "inherit",
  });
}
