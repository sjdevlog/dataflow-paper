export const C = {
  bg:          "#F5F3FB",
  card:        "#FFFFFF",
  cardBorder:  "#E8E4F4",

  main:        "#B8A9D9",
  mainDark:    "#5a4480",
  mainDim:     "#EAE5F5",

  point:       "#E8A0B4",
  pointDark:   "#D4849A",
  pointDim:    "#FCE8EE",
  sub:         "#D4849A",   // pointDark alias (OnboardingPage 호환)

  sky:         "#A8C4E0",
  skyDim:      "#DFF0F9",

  text:        "#3D3257",
  textDim:     "#7B6FA0",
  textMuted:   "#B0A8CC",

  inputBg:     "#F0EDF9",
  inputBorder: "#D8D0EE",

  error:       "#E87070",
  errorBg:     "#FDE8E8",
  warn:        "#D4900A",
  warnBg:      "#FFF6E0",
  warnBorder:  "#FFD54F",

  green:       "#388E3C",
  greenBg:     "#E8F5E9",
};

export const FONT = "'Noto Sans KR', sans-serif";

/** 공통 keyframes + reset */
export const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:none} }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }
  @keyframes popIn  { 0%{opacity:0;transform:scale(0.88)} 100%{opacity:1;transform:scale(1)} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.4} }
  @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
  @keyframes shake  { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-6px)} 75%{transform:translateX(6px)} }
  * { box-sizing:border-box; }
`;

/** 입력 폼(로그인·온보딩) 공통 스타일 + 모바일 대응 클래스 */
export const GS_FORM = GS + `
  input:focus { border-color:#B8A9D9 !important; outline:none; box-shadow:0 0 0 3px #B8A9D922; }
  input[type=range] { -webkit-appearance:none; appearance:none; height:4px; background:transparent; cursor:pointer; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:22px; height:22px; border-radius:50%; background:#B8A9D9; cursor:grab; border:3px solid #F5F3FB; box-shadow:0 2px 8px #B8A9D950; }
  @media (max-width:480px) {
    .df-title     { font-size:30px !important; }
    .df-step-title{ font-size:20px !important; }
    .df-inner     { padding-left:14px !important; padding-right:14px !important; padding-top:28px !important; }
    .df-nav-btn   { padding:12px !important; font-size:13px !important; }
  }
`;
