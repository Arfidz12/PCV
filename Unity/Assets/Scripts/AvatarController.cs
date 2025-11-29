using UnityEngine;

public class AvatarController : MonoBehaviour
{
    [Header("FBX Character (Optional)")]
    public GameObject fbxCharacter; // Assign your FBX character here
    
    private Animator animator;
    
    void Start()
    {
        // Prioritize FBX character if assigned
        if (fbxCharacter != null)
        {
            animator = fbxCharacter.GetComponent<Animator>();
            if (animator == null)
            {
                Debug.LogError("FBX character has no Animator component!");
                return;
            }
            
            // Check if humanoid
            if (animator.avatar != null && !animator.avatar.isHuman)
            {
                Debug.LogError("FBX character is not Humanoid!");
            }
        }
        else
        {
            // Use the default character on this GameObject
            animator = GetComponent<Animator>();
        }
        
        // Continue with your existing MediaPipe code...
    }
    
    void Update()
    {
        // Your existing update logic
    }
}