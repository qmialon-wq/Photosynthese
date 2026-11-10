import { test, expect, type Page } from "@playwright/test";

const id = "22222222-2222-4222-8222-222222222222";
const base = `/parcels/corpora/${id}`;

async function fixture(
  page: Page,
  role: "client" | "admin" = "client",
  unavailable = false,
) {
  await page.addInitScript(() =>
    localStorage.setItem("symbiose:data-mode:v1", "real"),
  );
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.abort(),
  );
  const writes: { path: string; body: Record<string, unknown> }[] = [];
  let videos: unknown[] = [],
    revision = 0,
    location: Record<string, unknown> | null = null;
  let profile: Record<string, unknown> = {},
    query: Record<string, unknown> | null = null;
  let dossier: Record<string, unknown> | null = null;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api/, "");
    const method = request.method();
    const body =
      method === "GET" || path.includes("/chunks/")
        ? {}
        : request.postDataJSON() || {};
    if (method !== "GET") {
      expect(request.headers()["x-csrf-token"]).toBe("client-test-token");
      writes.push({ path, body });
    }
    const reply = (value: unknown, status = 200) =>
      route.fulfill({ status, json: value });
    if (path === "/auth/me")
      return reply({
        user: {
          id: "owner",
          role,
          display_name: "Propriétaire",
          email: null,
          created_at: "2026-11-10",
          deleted_at: null,
        },
        csrf_token: "client-test-token",
      });
    if (path === "/console/uploads")
      return reply({ id: "upload", chunk_size: 4 }, 201);
    if (path.includes("/chunks/")) return reply({});
    if (path === "/console/uploads/upload/complete")
      return reply({ id: "import-task" }, 202);
    if (path === "/parcels/import-status") {
      videos = [
        {
          id: "video",
          filename: "terrain.mp4",
          status: "ready",
          metadata: {},
          created_at: "2026-11-10",
        },
      ];
      return reply([
        {
          id: "import-task",
          status: "completed",
          result: { video_id: "video" },
        },
      ]);
    }
    if (path === "/console/videos") return reply(videos);
    if (
      [
        "/review/species",
        "/review/samples",
        "/documents",
        "/console/tasks",
      ].includes(path)
    )
      return reply([]);
    if (path === "/parcels/options")
      return reply({
        land_types: { pasture: "Pâturage", woodland: "Bois", fallow: "Friche" },
        project_types: { housing: "Habitation", park: "Parc ou jardin" },
      });
    if (path === "/parcels/corpora") {
      if (method === "POST") {
        expect(body.video_ids).toEqual(["video"]);
        return reply({ id }, 201);
      }
      return reply([]);
    }
    if (path === base)
      return reply({
        id,
        actor: "owner",
        videos: [{ video_id: "video", filename: "terrain.mp4" }],
        profile: revision ? { revision, profile } : null,
        dossier,
      });
    if (path === base + "/territorial-context")
      return reply({ location, profile, profile_revision: revision, query });
    if (path === base + "/location") {
      expect(body.expected_revision).toBe(location?.revision || 0);
      location = {
        ...body,
        revision: Number(location?.revision || 0) + 1,
        actor: "owner",
        created_at: "2026-11-10",
      };
      return reply(location);
    }
    if (path === base + "/territorial-queries") {
      query = {
        id: "query",
        revision: Number(location?.revision || 1),
        status: "partial",
        obsolete: false,
        layers: {},
        result: null,
        created_at: "2026-11-10",
        inputs: {
          location,
          profile,
          profile_revision: revision,
          observations: [],
        },
        prefill: {
          values: unavailable
            ? {}
            : {
                area_m2: 1200 + Number(location?.revision || 1),
                locality: "Commune proposée",
                land_type: "pasture",
              },
          retrieved_at: "2026-11-10",
          notice: "Valeurs ouvertes à confirmer.",
        },
      };
      return reply({ id: "query", status: "pending" }, 202);
    }
    if (path === base + "/profile") {
      expect(body.expected_revision).toBe(revision);
      const { expected_revision: _, ...saved } = body;
      profile = saved;
      revision++;
      return reply({ revision, profile });
    }
    if (path === base + "/dossiers") {
      expect(body.profile_revision).toBe(revision);
      dossier = {
        id: "dossier",
        status: "running",
        profile_revision: revision,
        video_count: 1,
        completed_video_count: 1,
        videos: [],
        result: null,
      };
      return reply({ id: "dossier", status: "queued" }, 202);
    }
    return reply({ detail: "Pas de source de test" }, 404);
  });
  return writes;
}

for (const role of ["client", "admin"] as const) {
  test(`${role} : importer, créer, préremplir, corriger et modifier un dossier en cours`, async ({
    page,
  }) => {
    const writes = await fixture(page, role);
    await page.goto("/videos");
    await page
      .getByRole("button", { name: "Importer des vidéos", exact: true })
      .click();
    await page
      .getByLabel("Sélectionner des fichiers vidéo")
      .setInputFiles({
        name: "terrain.mp4",
        mimeType: "video/mp4",
        buffer: Buffer.from("fake-test-video-only"),
      });
    await page.getByRole("button", { name: "Envoyer les vidéos" }).click();
    await expect(
      page.getByText("terrain.mp4 · Import terminé, vidéo sélectionnée"),
    ).toBeAttached();
    await page.getByRole("button", { name: "Fermer la fenêtre" }).click();
    await page.getByRole("button", { name: /Préparer un dossier \(1/ }).click();
    await expect(page).toHaveURL(new RegExp(`/parcelles/${id}$`));
    await page.getByLabel("Latitude WGS84").fill("49.18");
    await page.getByLabel("Longitude WGS84").fill("-0.37");
    await page
      .getByRole("button", {
        name: "Enregistrer le point et préremplir",
        exact: true,
      })
      .click();
    await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveValue(
      "1201",
    );
    await expect(
      page.getByLabel("Commune ou secteur (modifiable)"),
    ).toHaveValue("Commune proposée");
    await expect(
      page.getByLabel("Type de parcelle", { exact: true }),
    ).toHaveValue("pasture");
    await page.getByLabel("Surface de la parcelle (m²)").fill("1500");
    await page
      .getByLabel("Commune ou secteur (modifiable)")
      .fill("Secteur corrigé manuellement");
    await page
      .getByLabel("Projet souhaité", { exact: true })
      .selectOption("housing");
    await page.getByLabel("Clôture", { exact: true }).check();
    await page
      .getByRole("button", {
        name: "Enregistrer mes modifications",
        exact: true,
      })
      .click();
    await expect(
      page.getByText("Modifications enregistrées.", { exact: true }),
    ).toBeVisible();
    await page.getByLabel("Latitude WGS84").fill("49.20");
    await page
      .getByRole("button", {
        name: "Enregistrer le point et préremplir",
        exact: true,
      })
      .click();
    await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveValue(
      "1500",
    );
    await expect(
      page.getByLabel("Commune ou secteur (modifiable)"),
    ).toHaveValue("Secteur corrigé manuellement");
    await page
      .getByRole("button", {
        name: "Analyser les vidéos et préparer mon dossier",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("button", { name: "Actualiser mon dossier", exact: true }),
    ).toBeDisabled();
    await page.getByLabel("Surface de la parcelle (m²)").fill("1600");
    await page
      .getByRole("button", {
        name: "Enregistrer mes modifications",
        exact: true,
      })
      .click();
    await expect
      .poll(
        () =>
          writes.filter((write) => write.path.endsWith("/profile")).at(-1)?.body
            .area_m2,
      )
      .toBe(1600);
    expect(
      writes.filter((write) => write.path.endsWith("/dossiers")),
    ).toHaveLength(1);
    expect(
      writes.find((write) => write.path.endsWith("/profile"))?.body
        .interventions,
    ).toEqual(["fencing"]);
    await page.screenshot({
      path: `test-results/client-form-${role}.png`,
      fullPage: true,
    });
  });
}

test("open data indisponible : enregistrer un brouillon puis renseigner tous les champs manuellement", async ({
  page,
}) => {
  const writes = await fixture(page, "client", true);
  await page.goto(`/parcelles/${id}`);
  await page.getByLabel("Latitude WGS84").fill("49.18");
  await page.getByLabel("Longitude WGS84").fill("-0.37");
  await page
    .getByRole("button", {
      name: "Enregistrer le point et préremplir",
      exact: true,
    })
    .click();
  await expect(
    page.getByText(/Préremplissage indisponible ou incomplet/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Enregistrer mes modifications", exact: true })
    .click();
  await expect
    .poll(
      () => writes.filter((write) => write.path.endsWith("/profile")).length,
    )
    .toBe(1);
  expect(
    writes.find((write) => write.path.endsWith("/profile"))?.body.area_m2,
  ).toBeNull();
  await page.getByLabel("Surface de la parcelle (m²)").fill("980");
  await page
    .getByLabel("Type de parcelle", { exact: true })
    .selectOption("woodland");
  await page
    .getByLabel("Projet souhaité", { exact: true })
    .selectOption("park");
  await page
    .getByLabel("Commune ou secteur (modifiable)")
    .fill("Secteur renseigné");
  await page
    .getByRole("button", {
      name: "Analyser les vidéos et préparer mon dossier",
      exact: true,
    })
    .click();
  await expect
    .poll(
      () => writes.filter((write) => write.path.endsWith("/dossiers")).length,
    )
    .toBe(1);
});
