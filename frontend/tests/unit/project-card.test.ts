import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";
import ProjectCard from "../../src/components/symbiose/ProjectCard.vue";
import VideoThumbnail from "../../src/components/VideoThumbnail.vue";
import type { Project } from "../../src/data/contracts";

const project: Project = {
  id: "parcel",
  name: "Parcelle du bois",
  videos: 0,
  species: 0,
  status: "unknown",
  project: "",
};
function render(value: Project) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div />" } }],
  });
  return mount(ProjectCard, {
    props: { project: value },
    global: { plugins: [router] },
  });
}
describe("miniatures des dossiers", () => {
  it("réutilise le lecteur de miniature de la première vidéo", () => {
    const previewVideo = {
      id: "first",
      filename: "premiere.mp4",
      source: "/api/console/videos/first/file",
      poster: "/first.jpg",
    };
    const wrapper = render({ ...project, videos: 2, previewVideo });
    expect(wrapper.getComponent(VideoThumbnail).props()).toMatchObject({
      source: previewVideo.source,
      poster: previewVideo.poster,
    });
    expect(wrapper.get("img").attributes("src")).toBe("/first.jpg");
    expect(wrapper.find(".sf-project-default").exists()).toBe(false);
    wrapper.unmount();
  });
  it("affiche l'illustration animale pour un dossier sans vidéo puis se met à jour", async () => {
    const wrapper = render(project);
    expect(wrapper.get(".sf-project-default").attributes("alt")).toContain(
      "Illustration par défaut",
    );
    expect(wrapper.findComponent(VideoThumbnail).exists()).toBe(false);
    await wrapper.setProps({
      project: {
        ...project,
        videos: 1,
        previewVideo: {
          id: "added",
          filename: "ajout.mp4",
          source: "/added.mp4",
          poster: "/added.jpg",
        },
      },
    });
    expect(wrapper.find(".sf-project-default").exists()).toBe(false);
    expect(wrapper.get("img").attributes("src")).toBe("/added.jpg");
    wrapper.unmount();
  });
});
