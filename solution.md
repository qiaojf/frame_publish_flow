这个怀疑对 **HTTPS** 有可能成立，但对我们当前这个 **HTTP 404** 基本可以排除。

FortiGate 官方配置里，HTTP Virtual Server 本身可以只配置 `server-type http`、80 端口和 Real Server，并不需要 TLS 证书；而 HTTPS Virtual Server 才配置 `ssl-certificate`。([Fortinet Docs][1])

更关键的是，我们已经有直接证据：

```text
外网 HTTP 请求
→ 115.179.103.225:80
→ FortiGate
→ 192.168.10.141
→ /var/log/nginx/access.log 有记录
→ Nginx 返回 404
```

如果 FortiGate 因“证书无效”而不放行这个域名，请求就不会到达 141。现在它已经到了 141，所以：

```text
HTTP 放行        ✅
FortiGate→141    ✅
证书拦截 HTTP    基本可排除
141 返回 404     ❌
```

证书确实会影响：

```text
https://tbpub.terabox.co.jp
                   ↑
                  443
```

如果你随便选了一个不包含 `tbpub.terabox.co.jp` 的证书，HTTPS 可能出现证书名称不匹配、TLS 错误或 FortiGate Virtual Server 配置异常。FortiGate 对用于 Virtual Server 的证书还有相应的 Web Server Authentication 要求。([Fortinet Community][2])

但它**不会解释现在 `http://...` 返回的 Nginx 404**。

所以当前我认为最值得查的仍然是 FortiGate 的 **HTTP Host 路由规则**。尤其是：

```text
Load Balance Method = HTTP Host

Real Server:
Host = tbpub.terabox.co.jp
IP   = 192.168.10.141
Port = 80
```

Fortinet 本身也说明，同一公网 IP 根据不同域名转发时，应使用 Virtual Server / Load Balance 的 `HTTP Host` 匹配。([Fortinet Community][3])

而且现在 `kado.terabox.co.jp` 也同样 404，这反而更像是 **FortiGate 的 Host 路由配置方式有问题**，而不是 tbpub 的证书单独有问题。

下一步先不要动证书。请把 FortiGate 中**一个目前正常工作的域名路由**和 **kado/tbpub 的域名路由**配置截图给我，我只对比这三条规则的差异。

[1]: https://docs.fortinet.com/document/fortigate/7.2.4/administration-guide/304594?utm_source=chatgpt.com "HTTP to HTTPS redirect for load balancing | FortiGate / FortiOS 7.2.4 | Fortinet Document Library"
[2]: https://community.fortinet.com/fortigate-3/technical-tip-certificate-does-not-appear-in-virtual-server-configuration-206485?utm_source=chatgpt.com "Technical Tip: Certificate does not appear in Virtual Server configuration | Community"
[3]: https://community.fortinet.com/support-forum-92/forward-url-205571?utm_source=chatgpt.com "Forward URL | Community"
