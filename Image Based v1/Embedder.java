import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import java.io.IOException;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.FileReader;
import java.io.FileNotFoundException;

public class Embedder
{
    static final int space=0;
    static final int period=27;
    static final int comma=28;
    static final int qmark=29; //qmark:=question mark
    static final int exclamation=30;
    static final int eom=31; //eom:= end of message

    public static void main(String[] args) throws IOException
    {
        String message[]=input();
        File imgFile = new File(message[0]);
        BufferedImage cover=ImageIO.read(imgFile);
        BufferedImage steganogram=embed(cover,message[1]);
        if(steganogram!=null)
            if(!ImageIO.write(steganogram,"png",new File("./ComGen.png")))
                System.out.println("Error! Steganogram not stored.");
            else
                System.out.println("\nSteganogram saved successfully.");
        else
            System.out.println("Try a larger image.");
    }
    /*
    Using String does not serve well when trying to embed messages which are very long ( beyond 4096 characters long on my
    machine ). Hence future implementations are to implement the input() method using File as the input object.
    */
    static String[] input()throws IOException
    {
        String inputs[]=new String[2];
        BufferedReader br=new BufferedReader(new InputStreamReader(System.in));
        System.out.print("Provide image:");
        inputs[0]=br.readLine();
        System.out.print("Enter text file containing the message:");
        inputs[1]=br.readLine();
        return inputs;
    }
    /*
        Only characters 'A'-'Z' and '.' , ',' , '?' , ' ' , '!' are embedded other characters like '$' and numbers are ignored.
    */
    static BufferedImage embed(BufferedImage img, String messageFile)throws FileNotFoundException, IOException
    {
        int x=0,y=0;
        int x_lim= img.getWidth(),y_lim=img.getHeight();
        long k;
        long pixel;
        FileReader mFile=new FileReader(messageFile);
        String sent_message=""; //debugging
        System.out.println("\nThe sent message is: " ); //debugging
        //for(i=0,m_len=message.length();i<m_len && x<x_lim;i++)
        int c=0;
        while((c=mFile.read())!=-1 && x<x_lim)
        {
            // all this is debugging
            // System.out.println(x);
            // System.out.println("Original RGB:"+((long)img.getRGB(x,y) & 0xffffffffL));
            char c_norm=(char)String.valueOf((char)c).toUpperCase().charAt(0);
            if((pixel=alterPixel(c_norm,img.getRGB(x,y)))==Long.MAX_VALUE)
            //this check looks allows the while loop to overlook characters outside this 32 character alphabet.
                continue;
            img.setRGB(x,y,(int)pixel);
            y=y+1;
            if(y==y_lim)
            {
                y=0;
                x++;
            }
            sent_message=sent_message+String.valueOf(c);//debugging
        }
        if(x!=x_lim)
            img.setRGB(x,y,(int)alterPixel((char)eom,img.getRGB(x,y)));
        else
        {
            System.out.println("...\n\nError! Image too small.");
            return null;
        }
        return img;
    }
    static long alterPixel(char c, long k)
    {
        k=k & 0xffffffffL;
        int alpha=(int) (k>>>24);
        int red=(int) (k>>16 & 0xff);
        int green=(int)(k>>8 & 0xff);
        int blue=(int)(k & 0xff);
        int true_c=0;
        int check=1;//this is used to check for legal characters
        if(c==31)
        {
            true_c=c;
            check=0;
        }
        else if(c>=65 && c<=90)
        {
            true_c=(c & 0xffff) -'A'+1;
            check=0;
        }
        else
            switch(c)
            {
                case ' ':
                true_c=space;
                check=0;
                break;
                case '.':
                true_c=period;
                check=0;
                break;
                case ',':
                true_c=comma;
                check=0;
                break;
                case '?':
                true_c=qmark;
                check=0;
                break;
                case '!':
                true_c=exclamation;
                check=0;
            }
        if(check!=0)
            return Long.MAX_VALUE;
        System.out.print(c);//Debugging: It prints the characters which are emdedded into the steganogram.
        red=(red & 252)+(true_c >>3);
        green=(green & 254)+(true_c >> 2 & 1);
        blue=(blue & 252)+(true_c & 3);
        long alteredPixel=0;
        alteredPixel=(alteredPixel+(alpha & 0xff))<<8; //the bitwise ands are not really necessary..
        alteredPixel=(alteredPixel+(red & 0xff))<<8;
        alteredPixel=(alteredPixel+(green & 0xff))<<8;
        alteredPixel=alteredPixel+(blue & 0xff);
        return alteredPixel;
    }
}
