<template>
  <!-- Original local vector artwork. Joint coordinates stay in the SVG viewBox;
       near/far limbs share a gait with an offset, including hock/knee flexion. -->
  <svg
    class="login-deer"
    viewBox="0 0 400 330"
    fill="currentColor"
    aria-hidden="true"
    focusable="false"
  >
    <g class="deer-body">
      <g class="deer-leg deer-hind deer-far">
        <path
          d="M133 165 Q117 163 111 182 L91 210 Q89 215 98 219 L117 222 L124 214 L108 208 L141 184Z"
        />
        <g class="deer-hind-shin">
          <path
            d="M118 213 Q123 211 125 218 L126 254 L117 283 L110 283 L117 252 L113 221Z"
          />
          <path d="M110 278 L119 280 L121 288 L107 288Z" />
        </g>
      </g>
      <g class="deer-leg deer-front deer-far">
        <path
          d="M244 162 Q259 164 258 182 L250 217 L238 219 L238 207 L241 181Z"
        />
        <g class="deer-front-shin">
          <path d="M239 211 L249 214 L244 253 L246 281 L238 284 L235 253Z" />
          <path d="M237 278 L246 277 L253 285 L237 288Z" />
        </g>
      </g>
      <!-- Rump, back, ribcage and rising neck form one uninterrupted silhouette. -->
      <path
        d="M107 147 Q97 138 93 140 L104 154 L114 159 Q111 182 132 196 Q146 203 165 197 Q194 207 221 195 Q239 199 252 180 Q264 160 273 145 L293 124 L281 107 Q264 111 253 133 L238 149 Q217 141 192 144 Q163 138 143 143 Q121 139 107 147Z"
      />
      <path
        class="deer-rim"
        d="M112 149 Q142 139 169 148 Q207 143 235 152"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      />
      <g class="deer-leg deer-hind deer-near">
        <path
          d="M136 168 Q119 166 115 186 L96 211 Q93 217 101 221 L120 224 L128 216 L111 209 L146 184Z"
        />
        <g class="deer-hind-shin">
          <path
            d="M121 215 Q126 212 128 220 L129 255 L120 284 L113 284 L120 253 L116 223Z"
          />
          <path d="M113 279 L122 281 L124 289 L110 289Z" />
        </g>
      </g>
      <g class="deer-leg deer-front deer-near">
        <path
          d="M237 165 Q252 165 252 183 L246 219 L234 221 L234 209 L235 184Z"
        />
        <g class="deer-front-shin">
          <path d="M235 213 L245 216 L240 254 L242 283 L234 286 L231 254Z" />
          <path d="M233 280 L242 279 L249 287 L233 290Z" />
        </g>
      </g>
      <g class="deer-head">
        <!-- Long muzzle, two pointed ears and branched, rigid antlers. -->
        <path
          d="M270 117 L277 101 Q280 95 290 98 L302 107 L325 114 Q330 117 326 123 L316 128 L294 124 L282 132Z"
        />
        <path
          d="M281 103 Q262 99 260 85 Q275 82 287 102 M290 102 Q290 83 305 79 Q307 94 294 107Z"
        />
        <g
          fill="none"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            stroke-width="5"
            d="M282 101 Q274 83 258 69 Q244 53 247 26 M289 100 Q288 76 294 62 Q307 44 305 19"
          />
          <path
            stroke-width="3"
            d="M255 65 L235 58 L227 45 M248 45 L234 31 L235 20 M247 31 L258 19 L259 10 M278 87 L263 84 L256 77 M294 65 L316 57 L326 42 M304 43 L319 31 L322 19 M306 29 L296 16 L297 7 M290 78 L309 75 L317 65"
          />
        </g>
        <path d="M313 116 L326 118 L324 123 L316 124Z" opacity=".5" />
        <circle cx="299" cy="111" r="1.8" class="deer-eye" />
      </g>
    </g>
  </svg>
</template>

<style scoped>
.login-deer {
  --deer-stride-duration: 600ms;
  --deer-far-offset: -130ms;
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}
.deer-body {
  transform-origin: 200px 170px;
  animation: deer-bound var(--deer-stride-duration) ease-in-out infinite;
}
.deer-leg {
  transform-box: view-box;
  animation: deer-reach var(--deer-stride-duration) linear infinite;
}
.deer-hind {
  transform-origin: 135px 176px;
}
.deer-front {
  transform-origin: 244px 173px;
  animation-name: deer-stride;
}
.deer-far {
  opacity: 0.65;
  animation-delay: var(--deer-far-offset);
}
.deer-hind-shin {
  transform-origin: 121px 219px;
  animation: deer-hock var(--deer-stride-duration) linear infinite;
}
.deer-front-shin {
  transform-origin: 241px 217px;
  animation: deer-knee var(--deer-stride-duration) linear infinite;
}
.deer-far :is(.deer-hind-shin, .deer-front-shin) {
  animation-delay: var(--deer-far-offset);
}
.deer-head {
  transform-origin: 277px 123px;
  animation: deer-steady var(--deer-stride-duration) ease-in-out infinite;
}
.deer-eye {
  fill: var(--sym-primary);
}
.deer-rim {
  color: white;
  opacity: 0.3;
}
@keyframes deer-bound {
  0%,
  100% {
    transform: translateY(0) rotate(-2deg);
  }
  25% {
    transform: translateY(5px) rotate(1deg);
  }
  60% {
    transform: translateY(-9px) rotate(-3deg);
  }
  80% {
    transform: translateY(-6px) rotate(-3deg);
  }
}
@keyframes deer-reach {
  0%,
  100% {
    transform: rotate(-32deg);
  }
  25% {
    transform: rotate(-8deg);
  }
  50% {
    transform: rotate(39deg);
  }
  75% {
    transform: rotate(18deg);
  }
}
@keyframes deer-stride {
  0%,
  100% {
    transform: rotate(-48deg);
  }
  25% {
    transform: rotate(-12deg);
  }
  50% {
    transform: rotate(38deg);
  }
  75% {
    transform: rotate(8deg);
  }
}
@keyframes deer-hock {
  0%,
  100% {
    transform: rotate(-22deg);
  }
  25% {
    transform: rotate(8deg);
  }
  50% {
    transform: rotate(-38deg);
  }
  75% {
    transform: rotate(-85deg);
  }
}
@keyframes deer-knee {
  0%,
  100% {
    transform: rotate(5deg);
  }
  25% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(-12deg);
  }
  75% {
    transform: rotate(-110deg);
  }
}
@keyframes deer-steady {
  0%,
  100% {
    transform: rotate(2deg);
  }
  25% {
    transform: rotate(-1deg);
  }
  60%,
  80% {
    transform: rotate(3deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .login-deer {
    display: none;
  }
  .login-deer * {
    animation: none;
  }
}
</style>
