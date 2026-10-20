include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-arthur
PKG_VERSION:=1.3.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-arthur
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=Arthur link status, uplink diagnostics and USB tethering control
  DEPENDS:=+luci-base +rpcd +uci +ubus +jsonfilter +ethtool-full +curl +ca-bundle +coreutils-timeout +kmod-tcp-bbr +kmod-sched +zram-swap
  PKGARCH:=all
endef

define Package/luci-app-arthur/description
  Show WAN, LAN1-3, USB link and USB bus speeds and control
  the persistent USB DHCP uplink. Run manual WAN/USB connectivity probes.
endef

define Package/luci-app-arthur/conffiles
/etc/config/arthur
endef

define Build/Compile
endef

define Package/luci-app-arthur/install
	$(INSTALL_DIR) $(1)
	$(CP) ./files/* $(1)/
	chmod 0755 $(1)/etc/init.d/arthur $(1)/etc/hotplug.d/net/90-f50 \
		$(1)/etc/uci-defaults/90-arthur-service $(1)/usr/libexec/arthur-usb \
		$(1)/usr/libexec/rpcd/arthur $(1)/usr/libexec/arthur-health \
		$(1)/etc/init.d/arthur-performance $(1)/usr/libexec/arthur-performance \
		$(1)/usr/libexec/arthur-performance-watch $(1)/etc/uci-defaults/91-arthur-performance
endef

$(eval $(call BuildPackage,luci-app-arthur))
