// 跳转登录的中转页（sso.html）。
// 博客 yuqianyi.com 拿不到 sutratoday.com 的登录 cookie，所以把读者送到这里：
// 已登录就向后端要一个一次性短码，带着它跳回原来的页面；没登录就先在这里登录或注册。
import { createSsoCode, getUser, whenAccountReady } from "./account-api.js?v=12";
import { openAccountDialog } from "./account.js?v=12";

// 允许跳回的站点（后端还会再核对一次）
const RETURN_ORIGINS = ["https://yuqianyi.com"];
const LOCAL_ORIGIN_RE = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;

const message = document.getElementById("sso-message");
const loginButton = document.getElementById("sso-login");
const backLink = document.getElementById("sso-back");

const returnTo = readReturn();
if (!returnTo) {
  message.textContent = "这个链接不完整，无法继续。";
  backLink.textContent = "去今文佛典首页";
  backLink.hidden = false;
} else {
  backLink.href = returnTo.href;
  loginButton.addEventListener("click", askLogin);
  whenAccountReady().then(() => (getUser() ? goBack() : askLogin()));
}

function readReturn() {
  try {
    const url = new URL(new URLSearchParams(location.search).get("return"));
    return RETURN_ORIGINS.includes(url.origin) || LOCAL_ORIGIN_RE.test(url.origin) ? url : null;
  } catch {
    return null;
  }
}

function askLogin() {
  message.textContent = `登录今文佛典账号后，会自动回到 ${returnTo.host} 继续评论。`;
  loginButton.hidden = false;
  backLink.hidden = false;
  openAccountDialog({ onSuccess: goBack });
}

async function goBack() {
  loginButton.hidden = true;
  backLink.hidden = true;
  message.textContent = `已登录为 ${getUser().username}，正在回到 ${returnTo.host}…`;
  try {
    const target = new URL(returnTo.href);
    target.hash = `sso=${await createSsoCode(returnTo.href)}`;
    location.replace(target.href);
  } catch (error) {
    // 登录已过期（request 已清掉本站登录态）或网络失败
    if (!getUser()) return askLogin();
    message.textContent = error.message || "出错了，请稍后再试";
    loginButton.hidden = true;
    backLink.hidden = false;
  }
}
