import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { clamp01 } from "./journey";
import { ownsPresentationKey } from "./jury-state";
import { narrativeDuration } from "./config";
import { pitchDuration, pitchSeconds, progressAtSeconds } from "./pitch";

gsap.registerPlugin(ScrollTrigger);

export class NarrativeTimeline {
  private context: gsap.Context;
  private trigger!: ScrollTrigger;
  private playback?: gsap.core.Tween;
  private state = { progress: 0 };
  private viewportWidth = 0;
  private viewportHeight = 0;
  private requestedProgress?: number;
  private nativeScrollOrigin?: number;
  private requestedScrollY = 0;
  private smooth!: gsap.QuickToFunc;
  constructor(
    private root: HTMLElement,
    private reduced: boolean,
    private onUpdate: (value: number) => void,
    private onPause: () => void,
  ) {
    this.context = gsap.context(() => {
      // Reuse a tween created before playback. Replacing it on each playback
      // tick would kill it before GSAP has rendered its first advancing frame.
      this.smooth = gsap.quickTo(this.state, "progress", {
        duration: 0.32,
        ease: "power1.out",
        onUpdate: () => this.onUpdate(this.state.progress),
        onComplete: () => {
          if (this.requestedProgress !== undefined) {
            this.state.progress = this.requestedProgress;
            this.onUpdate(this.state.progress);
          }
        },
      });
      this.trigger = ScrollTrigger.create({
        id: "symbiose-narrative",
        trigger: root,
        start: "top top",
        end: "bottom bottom",
        onUpdate: (trigger) => {
          // Scroll positions are rounded to physical pixels. Keep the exact
          // requested chapter boundary until native user input takes control.
          const progress = this.requestedProgress ?? trigger.progress;
          if (this.reduced) this.snap(progress);
          else this.smooth(progress);
        },
        onRefresh: (trigger) => {
          this.trigger = trigger;
          // GSAP also refreshes after its own resize debounce. Preserve an
          // explicit seek across that refresh, even when it arrives later.
          if (this.requestedProgress !== undefined) {
            const bounds = root.getBoundingClientRect();
            window.scrollTo({
              top:
                bounds.top +
                window.scrollY +
                this.requestedProgress *
                  Math.max(0, bounds.height - innerHeight),
              behavior: "instant",
            });
            this.requestedScrollY = window.scrollY;
            trigger.update();
          }
          this.snap(this.requestedProgress ?? trigger.progress);
        },
      });
    }, root);
    this.trigger = ScrollTrigger.getById("symbiose-narrative")!;
    // User input always takes back control; no wheel/touch event is prevented.
    window.addEventListener("wheel", this.interrupt, { passive: true });
    window.addEventListener("touchstart", this.interrupt, { passive: true });
    window.addEventListener("pointerdown", this.pointerInterrupt, {
      passive: true,
    });
    window.addEventListener("keydown", this.keyInterrupt);
    window.addEventListener("scroll", this.nativeScroll, { passive: true });
    document.addEventListener("visibilitychange", this.visibility);
  }
  private interrupt = (event?: Event) => {
    if (
      event?.target instanceof Element &&
      event.target.closest("dialog,.sx-recovery-tools,.jury-installation")
    ) {
      this.pause();
      return;
    }
    if (event?.type === "wheel" || event?.type === "touchstart") {
      // A wheel may only scroll the editorial panel. Keep exact chapter/video
      // ownership until the document actually moves, rather than sampling its
      // rounded physical position on pointer intent alone.
      this.nativeScrollOrigin = this.requestedProgress === undefined ? window.scrollY : this.requestedScrollY;
      this.pause();
      // With passive listeners Chromium may deliver the wheel event after its
      // compositor has already scrolled the document.
      this.nativeScroll();
      return;
    }
    this.requestedProgress = undefined;
    this.pause();
    // ScrollTrigger's wheel handler can sample the new scroll position before
    // this listener clears a programmatic destination. Resample after yielding.
    this.trigger.update();
    if (this.reduced) this.snap(this.trigger.progress);
    else this.smooth(this.trigger.progress);
  };
  private nativeScroll = () => {
    if (
      this.nativeScrollOrigin === undefined ||
      Math.abs(window.scrollY - this.nativeScrollOrigin) < 0.5
    )
      return;
    this.nativeScrollOrigin = undefined;
    this.interrupt();
  };
  private snap(progress: number) {
    const value = clamp01(progress);
    this.smooth(value, value);
    this.smooth.tween.progress(1).pause();
    this.state.progress = value;
    this.onUpdate(this.state.progress);
  }
  private pointerInterrupt = (event: PointerEvent) => {
    if (event.target === document.documentElement) this.interrupt();
  };
  private visibility = () => {
    if (document.hidden) this.pause();
  };
  private keyInterrupt = (event: KeyboardEvent) => {
    if (
      event.key === "Escape" ||
      event.key === "Tab" ||
      (event.target instanceof Element &&
        event.target.closest("dialog,video,input,select,textarea,summary"))
    ) {
      this.pause();
      return;
    }
    if (this.root.dataset.mode === "presentation" && ownsPresentationKey(event))
      return; // The presentation controller owns these keys, including Space toggle.
    // A focused control owns Space; let its native activation pause/play exactly once.
    if (
      event.key === " " &&
      event.target instanceof Element &&
      event.target.closest("button, a, input, select, textarea")
    )
      return;
    if (
      [
        "ArrowDown",
        "ArrowUp",
        "PageDown",
        "PageUp",
        "Home",
        "End",
        " ",
        "Escape",
        "Tab",
      ].includes(event.key)
    )
      this.interrupt();
  };
  seek(progress: number, immediate = false) {
    this.pause();
    this.scrollTo(progress);
    if (immediate) this.snap(progress);
  }
  private scrollTo(progress: number) {
    this.nativeScrollOrigin = undefined;
    this.requestedProgress = clamp01(progress);
    if (
      this.viewportWidth !== window.innerWidth ||
      this.viewportHeight !== window.innerHeight
    )
      this.refresh();
    const bounds = this.root.getBoundingClientRect();
    window.scrollTo({
      top:
        bounds.top +
        window.scrollY +
        clamp01(progress) * Math.max(0, bounds.height - window.innerHeight),
      behavior: "instant",
    });
    this.requestedScrollY = window.scrollY;
    // Synchronize programmatic seeks before a queued viewport refresh can sample
    // an outdated scroll position. Camera interpolation stays on the scrub tween.
    this.trigger.update();
    if (this.reduced) this.snap(this.requestedProgress);
    else this.smooth(this.requestedProgress);
  }
  play() {
    if (this.reduced) return;
    this.pause();
    const cursor = {
      value: this.trigger.progress >= 0.999 ? 0 : this.trigger.progress,
    };
    this.playback = gsap.to(cursor, {
      value: 1,
      duration: narrativeDuration * (1 - cursor.value),
      ease: "none",
      onUpdate: () => this.scrollTo(cursor.value),
      onComplete: () => this.pause(),
    });
  }
  /** Advance one continuous five-minute clock, including the demonstration chapter. */
  playPresentation() {
    if (this.reduced) return;
    this.pause();
    const cursor = { seconds: pitchSeconds(this.trigger.progress) };
    this.playback = gsap.to(cursor, {
      seconds: pitchDuration,
      duration: Math.max(.01, pitchDuration - cursor.seconds),
      ease: "none",
      onUpdate: () => this.scrollTo(progressAtSeconds(cursor.seconds)),
      onComplete: () => { this.scrollTo(1); this.snap(1); this.pause(); },
    });
  }
  /** Advance to a specified position. */
  playTo(progress: number, seconds: number) {
    if (this.reduced) return;
    this.pause();
    const target = clamp01(progress);
    const cursor = { value: this.trigger.progress };
    this.playback = gsap.to(cursor, {
      value: target,
      duration: Math.max(0.01, seconds),
      ease: "none",
      onUpdate: () => this.scrollTo(cursor.value),
      onComplete: () => {
        this.scrollTo(target);
        this.snap(target);
        this.pause();
      },
    });
  }
  pause() {
    this.playback?.kill();
    this.playback = undefined;
    this.onPause();
  }
  refresh() {
    // Preserve the requested scroll position, not the camera's lagging scrub value.
    const progress = this.requestedProgress ?? this.trigger.progress;
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
    // Global refresh also clears GSAP's cached viewport height. Refreshing only
    // this trigger can otherwise retain the previous window size until debounce.
    ScrollTrigger.refresh();
    this.scrollTo(progress);
    this.trigger.update();
    this.snap(progress);
  }
  dispose() {
    this.pause();
    this.smooth.tween.kill();
    this.context.revert();
    window.removeEventListener("wheel", this.interrupt);
    window.removeEventListener("touchstart", this.interrupt);
    window.removeEventListener("pointerdown", this.pointerInterrupt);
    window.removeEventListener("keydown", this.keyInterrupt);
    window.removeEventListener("scroll", this.nativeScroll);
    document.removeEventListener("visibilitychange", this.visibility);
  }
}
