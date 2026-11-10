import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import VideoThumbnail from "../../src/components/VideoThumbnail.vue";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("miniatures des vidéos réelles", () => {
  it("extrait une image au milieu puis libère le lecteur", async () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    const draw = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage: draw,
    } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue(
      "data:image/jpeg;base64,middle",
    );
    vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
    const wrapper = mount(VideoThumbnail, {
      props: { source: "/api/video/file", label: "Vidéo du terrain" },
    });
    await flushPromises();
    const media = wrapper.get("video");
    const video = media.element as HTMLVideoElement;
    Object.defineProperties(video, {
      duration: { value: 18.4 },
      videoWidth: { value: 1920 },
      videoHeight: { value: 1080 },
      readyState: { value: 2 },
    });
    await media.trigger("loadedmetadata");
    expect(video.currentTime).toBeCloseTo(9.2);
    await media.trigger("seeked");
    expect(draw).toHaveBeenCalledWith(video, 0, 0, 480, 270);
    expect(wrapper.get("img").attributes("src")).toBe(
      "data:image/jpeg;base64,middle",
    );
    expect(wrapper.find("video").exists()).toBe(false);
    wrapper.unmount();
  });
  it("retombe sur la vidéo si un poster manque, et signale un média illisible", async () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    const wrapper = mount(VideoThumbnail, {
      props: {
        source: "/api/video/file",
        poster: "/missing.jpg",
        label: "Miniature",
      },
    });
    await wrapper.get("img").trigger("error");
    await flushPromises();
    expect(wrapper.get("video").attributes("src")).toBe("/api/video/file");
    await wrapper.get("video").trigger("error");
    expect(wrapper.text()).toContain("Aperçu indisponible");
    expect(wrapper.find("img").exists()).toBe(false);
    wrapper.unmount();
  });
});
