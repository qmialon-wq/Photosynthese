import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TerritorialReport from "../../src/components/TerritorialReport.vue";
import { articleHref } from "../../src/source-links";

describe("sources du dossier", () => {
  it("remplace les références dans le texte par le titre lié sans doublon", () => {
    const wrapper = mount(TerritorialReport, {
      props: {
        dossierId: "existing-snapshot",
        report: {
          status: "generated",
          coverage: { documents_read: 2, documents_total: 2 },
          ledger: [
            {
              citation: "D319",
              title: "Haies <et> biodiversité",
              doi: "10.1234/hedges",
            },
            {
              citation: "D2",
              title: "Vie urbaine",
              findings: [{ source_url: "https://example.org/article.pdf" }],
            },
          ],
          pages: [
            {
              title: "Diagnostic",
              paragraphs: [
                {
                  text: "Selon [D319], conserver les haies.",
                  citations: ["D319", "D2"],
                },
              ],
            },
          ],
          actions: [],
        },
      },
    });
    const links = wrapper.findAll('a[href="https://doi.org/10.1234/hedges"]');
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Haies <et> biodiversité");
    expect(links[0].attributes("target")).toBe("_blank");
    expect(links[0].attributes("rel")).toContain("noopener");
    expect(
      wrapper.find('a[href="https://example.org/article.pdf"]').text(),
    ).toBe("Vie urbaine");
    expect(wrapper.text()).not.toContain("D319");
    expect(wrapper.find("et").exists()).toBe(false);
    wrapper.unmount();
  });

  it("refuse les URL exécutables et utilise le PDF local si nécessaire", () => {
    expect(
      articleHref({
        citation: "D1",
        title: "Unsafe",
        source_url: "javascript:alert(1)",
      }),
    ).toBeNull();
    expect(
      articleHref({
        citation: "D1",
        title: "Local",
        id: "doc",
        findings: [{ asset_id: "asset" }],
      }),
    ).toBe("/api/documents/doc/assets/asset?inline=true");
  });
});
