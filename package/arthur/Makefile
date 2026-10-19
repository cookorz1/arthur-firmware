include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-arthur
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-arthur
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=Arthur Ethernet link status and F50 USB uplink control
  DEPENDS:=+luci-base +rpcd +uci +ubus +jsonfilter +ethtool-full
  PKGARCH:=all
endef

define Package/luci-app-arthur/description
  Show the negotiated physical link speed of WAN and LAN1-3 and control
  the persistent F50 USB DHCP uplink from the LuCI interface.
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
		$(1)/usr/libexec/rpcd/arthur
endef

$(eval $(call BuildPackage,luci-app-arthur))
