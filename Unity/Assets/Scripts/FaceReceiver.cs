using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// Attach this to avatar root. Assign SkinnedMeshRenderer and headBone.
public class FaceReceiver : MonoBehaviour
{
    [Header("Network")]
    public int listenPort = 5065;

    [Header("Avatar")]
    public SkinnedMeshRenderer faceMeshRenderer;
    public Transform headBone;

    [Header("Blendshape mapping (use index or name)")]
    public int mouthOpenBlendIndex = -1;
    public int leftEyeBlinkBlendIndex = -1;
    public int rightEyeBlinkBlendIndex = -1;
    public int leftBrowRaiseBlendIndex = -1;
    public int rightBrowRaiseBlendIndex = -1;

    public string mouthOpenBlendName = "";
    public string leftEyeBlinkBlendName = "";
    public string rightEyeBlinkBlendName = "";
    public string leftBrowRaiseBlendName = "";
    public string rightBrowRaiseBlendName = "";

    [Header("Scales")]
    public float mouthOpenScale = 100f;
    public float eyeBlinkScale = 100f;
    public float browRaiseScale = 100f;
    public float headRotationScale = 1f;

    UdpClient udpClient;
    Thread listenThread;
    volatile bool running = false;

    volatile float mouthOpen = 0f;
    volatile float leftEyeOpen = 1f;
    volatile float rightEyeOpen = 1f;
    volatile float leftBrow = 0f;
    volatile float rightBrow = 0f;
    volatile float headPitch = 0f;
    volatile float headYaw = 0f;
    volatile float headRoll = 0f;

    void Start()
    {
        ResolveBlendshapeIndices();
        StartListener();
    }

    void OnDestroy()
    {
        StopListener();
    }

    void ResolveBlendshapeIndices()
    {
        if (faceMeshRenderer == null) return;
        var mesh = faceMeshRenderer.sharedMesh;
        if (mesh == null) return;

        if (mouthOpenBlendIndex < 0 && !string.IsNullOrEmpty(mouthOpenBlendName))
            mouthOpenBlendIndex = mesh.GetBlendShapeIndex(mouthOpenBlendName);
        if (leftEyeBlinkBlendIndex < 0 && !string.IsNullOrEmpty(leftEyeBlinkBlendName))
            leftEyeBlinkBlendIndex = mesh.GetBlendShapeIndex(leftEyeBlinkBlendName);
        if (rightEyeBlinkBlendIndex < 0 && !string.IsNullOrEmpty(rightEyeBlinkBlendName))
            rightEyeBlinkBlendIndex = mesh.GetBlendShapeIndex(rightEyeBlinkBlendName);
        if (leftBrowRaiseBlendIndex < 0 && !string.IsNullOrEmpty(leftBrowRaiseBlendName))
            leftBrowRaiseBlendIndex = mesh.GetBlendShapeIndex(leftBrowRaiseBlendName);
        if (rightBrowRaiseBlendIndex < 0 && !string.IsNullOrEmpty(rightBrowRaiseBlendName))
            rightBrowRaiseBlendIndex = mesh.GetBlendShapeIndex(rightBrowRaiseBlendName);

        Debug.Log($"FaceReceiver resolved blendshape indices: mouth={mouthOpenBlendIndex}, leftEye={leftEyeBlinkBlendIndex}, rightEye={rightEyeBlinkBlendIndex}, leftBrow={leftBrowRaiseBlendIndex}, rightBrow={rightBrowRaiseBlendIndex}");
    }

    void StartListener()
    {
        try
        {
            udpClient = new UdpClient(listenPort);
            running = true;
            listenThread = new Thread(ListenLoop);
            listenThread.IsBackground = true;
            listenThread.Start();
            Debug.Log($"FaceReceiver listening on UDP {listenPort}");
        }
        catch (Exception e)
        {
            Debug.LogError("FaceReceiver start error: " + e);
        }
    }

    void StopListener()
    {
        running = false;
        try { udpClient?.Close(); } catch { }
        if (listenThread != null && listenThread.IsAlive) listenThread.Join(200);
    }

    void ListenLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                var data = udpClient.Receive(ref remoteEP);
                string json = Encoding.UTF8.GetString(data);
                ParseJson(json);
            }
            catch (SocketException) { }
            catch (Exception e)
            {
                Debug.LogWarning("FaceReceiver listen error: " + e);
            }
        }
    }

    [Serializable] class HeadObj { public float pitch; public float yaw; public float roll; }
    [Serializable] class MouthObj { public float open; }
    [Serializable] class EyeObj { public float open; }
    [Serializable] class BrowObj { public float left; public float right; }
    [Serializable] class FacePacket { public HeadObj head; public MouthObj mouth; public EyeObj left_eye; public EyeObj right_eye; public BrowObj brow; }

    void ParseJson(string json)
    {
        try
        {
            FacePacket pkt = JsonUtility.FromJson<FacePacket>(json);
            if (pkt == null) return;
            mouthOpen = pkt.mouth != null ? pkt.mouth.open : mouthOpen;
            leftEyeOpen = pkt.left_eye != null ? pkt.left_eye.open : leftEyeOpen;
            rightEyeOpen = pkt.right_eye != null ? pkt.right_eye.open : rightEyeOpen;
            leftBrow = pkt.brow != null ? pkt.brow.left : leftBrow;
            rightBrow = pkt.brow != null ? pkt.brow.right : rightBrow;
            if (pkt.head != null)
            {
                headPitch = pkt.head.pitch;
                headYaw = pkt.head.yaw;
                headRoll = pkt.head.roll;
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("FaceReceiver JSON parse error: " + e);
        }
    }

    void Update()
    {
        if (faceMeshRenderer != null)
        {
            if (mouthOpenBlendIndex >= 0)
                faceMeshRenderer.SetBlendShapeWeight(mouthOpenBlendIndex, Mathf.Clamp01(mouthOpen) * mouthOpenScale);

            if (leftEyeBlinkBlendIndex >= 0)
            {
                float leftBlink = (1f - Mathf.Clamp01(leftEyeOpen)) * eyeBlinkScale;
                faceMeshRenderer.SetBlendShapeWeight(leftEyeBlinkBlendIndex, leftBlink);
            }
            if (rightEyeBlinkBlendIndex >= 0)
            {
                float rightBlink = (1f - Mathf.Clamp01(rightEyeOpen)) * eyeBlinkScale;
                faceMeshRenderer.SetBlendShapeWeight(rightEyeBlinkBlendIndex, rightBlink);
            }

            if (leftBrowRaiseBlendIndex >= 0)
                faceMeshRenderer.SetBlendShapeWeight(leftBrowRaiseBlendIndex, Mathf.Clamp(leftBrow, -1f, 1f) * browRaiseScale);
            if (rightBrowRaiseBlendIndex >= 0)
                faceMeshRenderer.SetBlendShapeWeight(rightBrowRaiseBlendIndex, Mathf.Clamp(rightBrow, -1f, 1f) * browRaiseScale);
        }

        if (headBone != null)
        {
            Quaternion q = Quaternion.Euler(headPitch * headRotationScale, headYaw * headRotationScale, headRoll * headRotationScale);
            headBone.localRotation = q;
        }
    }
}