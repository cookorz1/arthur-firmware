# ��������ɪ AX1800 Pro ���Ʊ���

״̬����׼���˱�����Ŀ����δ���� Linux ���롢��δ���ɻ�ʵ����֤�̼���

## �����õĹ���

- LibWrt 25.12-nss��qualcommax/ipq60xx��ר���豸 `jdcloud_re-ss-01`�����ʵ�ײ��ͺ�Ϊ RE-SS-01��
- ���� LuCI �������棬iStore ԭ��Ӧ���̵꣬OpenClash������ʱ���ز����� Mihomo �ȶ��� ARM64 ���ġ�
- USB 3.0��CDC-ECM��RNDIS��CDC-NCM ������ usb-modeswitch��ZTE USB ��������ʱ���� DHCP �ӿ� `f50` ������ WAN ����ǽ����
- �նˡ�USB �洢��ext4 �͹��ع��ߣ����ں���ά����

F50 �� USB ��̫��ģʽʹ�ã�F50 �Լ����� SIM �����š�����Ŀ��������Ϊ���ڲ��š��Զ�ʶ�� ZTE USB ���� ID `19d2`���д�ʵ����֤������ ZTE USB ����Ҳ��ƥ�䡣�������� �� �ӿ����ֶ���� `f50` ��Ӧ�豸��

## �Ʊ���

1. �������� GitHub �ֿ⣬Ĭ�Ϸ�֧ʹ�� `main`����ʼ�� README��
2. �ѱ�Ŀ¼�ڵ��ļ����ڲֿ��Ŀ¼������ `.github/workflows/build.yml`����Ҫ�� `arthur-firmware` ���㵱���ֿ���Ŀ¼�ϴ�����������Ϸſ���©������Ŀ¼������������ GitHub �� Add file �� Create new file �������ļ�����д `.github/workflows/build.yml` ��ճ������Ŀͬ���ļ����ݡ�
3. �ύ�ᴥ�����룬Ҳ�ɴ� Actions �� Build Arthur F50 OpenClash iStore �� Run workflow��
4. ��ȫ������ɹ����ڸô����е� Artifacts ���� `Arthur-F50-OpenClash-iStore-*`��
5. ���ʧ�ܣ�������־�����Ų飻ʧ�����в��ṩ������ɹ����Ĺ̼����

�̶�����Դ�롢OpenClash��iStore ���ύ������ feeds �� Mihomo �ȶ����ڱ���ʱ����������ʵ�ʰ汾�����á����嵥��У��ֵһ�𱣴档���α䶯�����������Կ��ܵ����״α�����Ҫ������

## Ĭ������

- ������ַ��http://192.168.10.1 ���ܿ� F50 �����Ĺ������Σ�
- �û�����root������Դ�����Ԥ�����뷽ʽ���״ν���������������롣
- ʱ�����й��Ϻ����������������豸Դ��Ĭ��ֵ���������ҳ������ Wi-Fi��
- OpenClash �赼���Լ��Ķ��Ļ����ú�������Ŀ���������Ļ�ڵ�ƾ�ݡ�
- iStore ��ѡ�У��̵��ڸ���Ӧ�ÿ����ܼܹ��������������̼��汾���ں�ģ���������ơ�����Ӧ���̵겻�������� iStoreOS��Ҳ����֤ÿ��Ӧ�ÿɰ�װ��
- ����Դ��� NSS ���Ĭ�����á����������ܷ�ʹ�ü���ȡ���� OpenClash �Ĺ���ģʽ������֤���������� NSS��

## �̼������

���޸ķ���������д U-Boot����ˢ�豸������ʹ��Դ���豸Ĭ�Ͼ����ʽ������飺�豸ѡ��ͱ�Ҫ���������ں˲��������� 6144 KiB ��λ��factory �� sysupgrade ��������ڡ����嵥������ÿ�����񲻳������ص� 60 MiB ���ޡ�

��Щ��鲻��ȷ���㵱ǰ·������ʵ�ʷ�����ˢ��ǰ����鿴��ǰϵͳ�ʹ��̲��֣����ܽ�ƾ�ļ����е� factory/sysupgrade �����ܷ�ˢ�룬����ǿ����������У�顣

��·���� SSH �п�ִ������ֻ�����������ṩ��Э����ȷ�ϣ�

```sh
ubus call system board
cat /proc/partitions
cat /proc/mtd
ls -l /dev/disk/by-partlabel 2>/dev/null
lsblk -o NAME,SIZE,TYPE,FSTYPE,PARTLABEL,MOUNTPOINTS 2>/dev/null
```

## ��Դ

- https://github.com/LiBwrt/LibWrt
- https://github.com/vernesong/OpenClash
- https://github.com/istoreos/istore
- https://github.com/MetaCubeX/mihomo
